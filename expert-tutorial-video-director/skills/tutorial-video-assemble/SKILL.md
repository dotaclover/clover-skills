---
name: tutorial-video-assemble
description: Assemble a tutorial video from a beats list — record real browser/desktop operations with ffmpeg, synthesize per-beat dubbing with edge-tts at -16 LUFS, generate sentence-timed subtitles, and render the final cut. Use when the user wants to record a screen demo, dub narration, add or burn subtitles, cut clips into a finished video, or re-cut an existing episode.
agent_created: true
---

# 实拍、配音、字幕、出片

这一段吃 `beats.json` 和素材，吐出成片。**音频定节奏**：先配音拿到真实时长，再决定卡片停多久、录屏压几倍。反过来一定返工。

字段定义见 `references/beats契约.md`（唯一权威）。画布、卡片、台词怎么写不在这里——那分别归 `svg-lecture-deck` 和 `tutorial-series-plan`。

## 录制实拍

先查浏览器里有没有还开着的页面，**有就复用**，不要为了录屏把任务重跑一遍。

```bash
python scripts/record_window.py --list
python scripts/record_window.py --title "Edge" --duration 300 \
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
python scripts/build_film.py --ep episodes/EP01                    # 只出 build/ 产物
python scripts/build_film.py --ep episodes/EP01 --render --subs    # 出片 + 烧字幕
python scripts/build_film.py --ep episodes/EP01 --force            # 改过台词必须加
python scripts/build_film.py --ep episodes/EP01 --fit stretch      # 配音超长时降速兜住
python scripts/build_film.py --ep episodes/EP01 --preset 9:16      # 临时换画布
```

它会做：逐段 TTS（带缓存）→ 响度归一 `I=-16` → 卡片静帧片段 → 组装 `config.json` → 生成 SRT → 打表。

画布缺省取 `beats.json` 的 `canvas`；没写就是 1920×1080。预设表和令牌在 `svg-lecture-deck/scripts/canvas.py`——**两个技能必须一起装**，卡片 SVG 的渲染脚本也在那边。

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

同一条文字重跑会命中缓存；**改了台词不加 `--force`，听到的是上一版**——这是最常见的返工原因。

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
| 字幕和声音错位 | 改台词没加 `--force` |
| 竖屏成片两边有黑边 | 素材是横屏。`resize_mode=contain` 只缩不放，竖屏要重新录或重新做卡 |
| 录制文件打不开 | 被 kill 了，用 `--stop-file` 重录 |

## 依赖

- 本机 `ffmpeg` / `ffprobe`（默认 `C:/ffmpeg/bin/`，`--ffmpeg/--ffprobe` 可覆盖）
- `edge-tts`（见 `requirements.txt`）
