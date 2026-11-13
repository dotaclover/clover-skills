---
name: tutorial-video-assemble
description: Assemble a tutorial video from a beats list — record real browser/desktop operations with ffmpeg, synthesize per-beat dubbing with edge-tts at -16 LUFS, generate sentence-timed subtitles, and render the final cut. Use when the user wants to record a screen demo, dub narration, add or burn subtitles, cut clips into a finished video, or re-cut an existing episode.
agent_created: true
---

# 实拍、配音、字幕、出片

这一段吃 `beats.json` 和素材，吐出成片。**音频定节奏**：先配音拿到真实时长，再决定卡片停多久、录屏压几倍。反过来一定返工。

字段定义见 `references/beats契约.md`（唯一权威）。画布、卡片、台词怎么写不在这里——那分别归 `svg-lecture-deck` 和 `tutorial-series-plan`；这说的是**知识分工**，不是安装依赖：本技能自带 `canvas.py`、`svg2png.py`、`video_pipeline.py`，整目录拷走单独也能跑。

## 路径与安全边界

从当前加载的 `SKILL.md` 定位实际技能目录，下文 `<技能目录>` 指该目录，不依赖项目中存在 `expert/skills`。输入集目录只读；每次指定全新的独立 `--work-dir`，渲染还需新的 `--output-dir`，二者均不得包含彼此或位于输入集目录内。已有目录直接拒绝，不删除历史产物。

默认不联网。每段优先读取 `voice_file`（相对集目录或绝对路径），否则复用内容寻址的配音缓存；缺缓存则停止。只有用户明确同意把台词发送至在线 TTS 后才传 `--allow-tts-network`。离线配音由用户预先归一响度，脚本不改原音频。可用 `--cache-dir` 跨运行复用缓存。

## 录制实拍

先查浏览器里有没有还开着的页面，**有就复用**，不要为了录屏把任务重跑一遍。

```bash
python "<技能目录>/scripts/record_window.py" --list
python "<技能目录>/scripts/record_window.py" --title "Edge" --duration 300 \
       --out rec/demo01.mp4 --stop-file build/stop
touch build/stop          # 操作完收尾
```

- 录制在后台起，`--duration` 只作兜底；停的时候用 `--stop-file`，**绝不 kill 进程**（moov 写不进去，文件就打不开）。
- 脚本会自动最大化 + 置前，画面里只有这一个应用；`--no-max` 保留原窗口。
- gdigrab 只读像素不抢焦点，录制期间可以正常操作。
- 一次录一个完整任务，剪辑点后期在 `beats.json` 里定；原片永不改写。
- 等待段不要剪掉，压速就是证据（细则见 `references/录屏.md`）。

## 配音与出片

```bash
python "<技能目录>/scripts/build_film.py" --ep episodes/EP01 --work-dir work/run01
python "<技能目录>/scripts/build_film.py" --ep episodes/EP01 --work-dir work/run02 --output-dir out/run02 --render --subs
# 仅在用户授权在线配音后使用；不授权时优先 voice_file 或已有缓存
python "<技能目录>/scripts/build_film.py" --ep episodes/EP01 --work-dir work/run03 --cache-dir cache/tts --allow-tts-network
```

可选 `--fit stretch` 自动延长实拍槽位，`--preset 9:16` 覆盖画布；`--force` 忽略配音缓存但不授予联网权限。

它会做：逐段 TTS（带缓存）→ 响度归一 `I=-16` → 卡片静帧片段 → 组装 `config.json` → 生成 SRT → 打表。

画布缺省取 `beats.json` 的 `canvas`；没写就是 1920×1080。预设表和令牌在本技能的 `scripts/canvas.py`，卡片 SVG 的渲染脚本是同目录的 `scripts/svg2png.py`——**这两个文件都随本技能一起走**，不需要别的技能在场。

### 看那张表

```
段     类型      槽位    配音    余量  字数  判定
d3     demo     9.60    9.44    0.16    14  OK
w3     demo    25.36   31.02   -5.66   104  OVER
```

`OVER` = 台词超了槽位。三种处理，**按顺序试**：

1. **砍字**（首选）。砍到 90 字以内通常就够。
2. **`--fit stretch`**。自动降速画面把配音兜住，只适合实拍段（卡片段时长本来就跟着配音走）。
3. 重录更长的素材。

缓存键包含文本、音色、语速、音量与响度参数；改台词自动换键，不会误用旧配音。录屏默认拒绝已有文件，只有明确 `--overwrite` 才覆盖；已有 stop-file 也会拒绝，不主动删除。SVG 渲染拒绝已有图片。

### 字幕

`--subs` 打开 `subtitle_mode=burn`，同时导出 `subtitles.srt`。

字幕由本段台词按字数比例摊到配音时长上，**相对片段**计时，不是 ASR、没有逐字时间戳。所以单条 ≤ 26 字，靠逗号断句。

**竖屏 + 烧字幕要谨慎**：渲染器的字幕贴底（MarginV 16），在手机上会被平台 UI 压住。竖屏优先只出 SRT 走平台 CC，或者把要点做进卡片。

## 验收

**没抽帧看过不算做完。**

```bash
ffmpeg -y -i out/EP01_render/final.mp4 -vf "fps=1/10,scale=420:-1,tile=5x6" -frames:v 1 _sheet.jpg
ffmpeg -nostats -i out/EP01_render/final.mp4 -af ebur128=peak=true -vn -f null - 2>&1 | grep -E "^ *I:"
ffmpeg -i out/EP01_render/final.mp4 -af "silencedetect=noise=-32dB:d=1.2" -vn -f null - 2>&1 | grep silence_
```

逐项核：时长合理、卡片文字没被裁、录屏没有卡在无关画面、字幕没压关键区域、段落中间没有 1 秒以上静音。

## 交付

`final.mp4` + `report.json` + `subtitles.srt` + `<EP>_台词稿.md` + `plan.csv`。
说明规格、字幕是近似摊时、哪几段压了速、哪些功能"还没拍"。

## 坑

| 现象 | 原因 |
|---|---|
| 渲染报"片段范围越界" | segment `end` 用了设定值；`build_film.py` 会自动取实测时长，别手改 config |
| 渲染报"找不到 source" | 路径相对 `config.json` 目录（`build/`）写错，脚本已自动算，手改过才会错 |
| 某段静音 | `audio_mode=replace` 下每段必须有 `voice_file`；无台词段把 `text` 留空会自动补静音 |
| 字幕和声音错位 | 离线 voice_file 与台词不一致，或按字数摊时误差 |
| 竖屏成片两边有黑边 | 素材是横屏。`resize_mode=contain` 只缩不放，竖屏要重新录或重新做卡 |
| 录制文件打不开 | 被 kill 了，用 `--stop-file` 重录 |

## 依赖

- 本机 `ffmpeg` / `ffprobe`（优先 PATH，兼容探测 `C:/ffmpeg/bin/`，`--ffmpeg/--ffprobe` 可覆盖）
- `edge-tts` 仅在线配音需要（见 `requirements.txt`）；离线配音无需安装
