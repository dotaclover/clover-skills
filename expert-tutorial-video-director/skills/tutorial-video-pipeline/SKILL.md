---
name: tutorial-video-pipeline
description: End-to-end pipeline for producing serialized tutorial videos: outline a series, write beats and narration, design 1920x1080 SVG lecture cards and export them as PPTX, record real browser/desktop operations with ffmpeg, synthesize per-beat dubbing with edge-tts, generate burned subtitles, and render the final cut. Use when the user asks to plan, build, record, dub, subtitle or re-cut a tutorial/course video series.
agent_created: true
---

# 系列教程视频流水线

一条命令级的干活流程：**主题 → 分镜台词 → SVG 讲义卡 / PPT → 浏览器实拍 → 配音 → 字幕 → 成片**。

核心原则：**音频定节奏，画面跟着音频长。** 先写台词，先配音，拿到每段真实时长，再决定卡片停多久、录屏压多少倍速。反过来做（先剪画面再配音）一定会返工。

---

## 项目结构

```
<项目>/
  series.json               全系列：风格色板、音色、固定开头/结尾、分集表
  assets/cards/             跨集复用卡片（片头、结束卡、作业黑板）
  episodes/EP01/
    beats.json              本集唯一真相：分镜顺序 + 每段台词
    cards/                  本集 SVG 源（1920×1080）
    cards_png/              SVG 渲染产物（不要手改）
    rec/                    浏览器/桌面实拍原片（只读，永不改写）
    build/                  audio/ clips/ config.json plan.csv 台词稿
    out/                    成片
```

`beats.json` 是所有环节的唯一输入。改内容只改它，然后重跑构建。

```json
{
  "episode": "EP01",
  "title": "大模型与智能体差在哪",
  "canvas": {"width": 1920, "height": 1080, "fps": 30},
  "voice": {"name": "zh-CN-YunxiNeural", "rate": "+8%", "volume": "+0%"},
  "loudnorm": "loudnorm=I=-16:TP=-1.5:LRA=11",
  "card_tail": 0.9,
  "beats": [
    {"id": "c01", "kind": "card", "png": "C01_片头.png", "text": "…"},
    {"id": "d1", "kind": "demo", "src": "demo01.mp4", "start": 3.4, "end": 23.5,
     "speed": 4.0, "text": "对着画面说正在发生什么 …"},
    {"id": "c99", "kind": "card", "png": "C99_结束卡.png", "text": "我是顺哥，我们下个视频见。"}
  ]
}
```

- `kind: card` —— 静帧卡片，时长 = 配音 + `card_tail`。
- `kind: demo` —— 实拍片段，`start/end` 是**原片**时间，`speed` 是播放倍速，输出时长 = `(end-start)/speed`。
- `text` 为空串表示纯画面段（自动补静音），默认不要用。
- `png` 写错、源文件缺失、范围越界，脚本会直接报出来，不会静默跳过。

---

## 七步 SOP

### Step 0 · 立项（每系列一次）

```bash
python scripts/init_project.py --root <项目目录> --title "系列名" --episodes 6
```

然后填 `series.json`：受众基础、一句话承诺、固定开头结尾、色板与音色。
**分集表要先定每集一句话目标**，一句说不清就是选题没想好，别开做。

### Step 1 · 单集分镜与台词

先在 `beats.json` 里把顺序写死，再写台词。规则：

1. **开场 15 秒给结果**，不给概念。观众第一眼看的是"这东西能做出什么"，不是"什么是大模型"。
2. **card 与 demo 交替**：每讲完一个抽象点，立刻接一段实拍；每段实拍结束，立刻用卡片收口。
3. 单段台词 **40–90 字**（约 8–18 秒）。超过 100 字必拆。
4. 台词对着画面写。画面里没有的东西不要念（"它能自动发邮件"——没拍就不说）。
5. 每集固定骨架：`片头卡 → 钩子 → 正文（card/demo 交替）→ 对照卡 → 收尾卡 → 作业黑板 → 结束卡`。

### Step 2 · 讲义卡：SVG → PNG → PPT

卡片是 **SVG 源文件**，一个字都能改；PNG 只是渲染产物。同一批 SVG 同时喂视频和 PPT，两边不走形。

```bash
# 渲染（Edge 无头，串行）
python scripts/svg2png.py --svg-dir episodes/EP01/cards --out-dir episodes/EP01/cards_png

# 导出 PPT（每张卡一页，台词自动写进备注）
python scripts/svg2pptx.py --png-dir episodes/EP01/cards_png \
       --out episodes/EP01/out/EP01_讲义.pptx --beats episodes/EP01/beats.json
```

设计规范见 `references/讲义卡规范.md`：1920×1080、安全边 135px、标题 72、正文 40–48、四叶草色板。
**每张卡只讲一件事**，一屏塞三个论点等于没讲。

### Step 3 · 浏览器实拍

先查有没有已开着的页面，有就复用，不要重跑任务重新生成一遍。

```bash
python scripts/record_window.py --list                      # 看窗口标题
python scripts/record_window.py --title "Edge" --duration 300 \
       --out episodes/EP01/rec/demo01.mp4 --stop-file build/stop
```

- 录制在后台起，`--duration` 只作兜底；操作完 `touch build/stop` 让 ffmpeg 优雅收尾。
- 录制前脚本会自动最大化 + 置前，画面干净。
- 录制中可以用浏览器工具/键鼠脚本正常操作，gdigrab 只读像素不抢焦点。
- **等待段不要剪掉**：那是"它真的在干活"的证据，后期压速即可（3–4 倍）。
- 原片永不改写；要换剪辑点就改 `beats.json` 的 `start/end`。

### Step 4 · 配音与时长核对

```bash
python scripts/build_film.py --ep episodes/EP01            # 只出 build/ 产物
```

脚本做的事：edge-tts 逐段合成（带缓存）→ 响度归一 `I=-16` → 卡片静帧片段 → 组装 `config.json` → 输出 `plan.csv` 和台词稿。

看控制台那张表：

```
段     类型      槽位    配音    余量  字数  判定
d3     demo     9.60    9.44    0.16    14  OK
w3     demo    25.36   31.02   -5.66   104  OVER
```

- `OVER` = 台词太长，画面装不下。三种处理：砍字（首选）→ 提速画面（`--fit stretch`）→ 重录。
- 同一条文字重跑会被缓存跳过；改了台词必须 `--force`，否则拿到的是旧音频。

### Step 5 · 组装与渲染

```bash
python scripts/build_film.py --ep episodes/EP01 --render            # 出片
python scripts/build_film.py --ep episodes/EP01 --render --subs     # 带烧录字幕
```

底层调 `scripts/video_pipeline.py render`（配置驱动渲染器，见 `references/渲染配置.md`）。默认：1920×1080 / 30fps / CRF 20 / `audio_mode=replace` / 不烧字幕。

字幕由本段配音时长按字数比例分摊生成，**相对片段**计时；开 `--subs` 时同时导出 SRT。

### Step 6 · 验收（不做这一步不算交付）

```bash
# 整体抽帧：每 10 秒一格，看有没有黑帧/错段
ffmpeg -y -i out/EP01_render/final.mp4 -vf "fps=1/10,scale=420:-1,tile=5x6" -frames:v 1 _sheet.jpg

# 响度与静音断点
ffmpeg -nostats -i out/EP01_render/final.mp4 -af ebur128=peak=true -vn -f null - 2>&1 | grep -E "^ *I:|Peak:"
ffmpeg -i out/EP01_render/final.mp4 -af "silencedetect=noise=-32dB:d=0.25" -vn -f null - 2>&1 | grep silence_
```

逐项核对：时长是否合理、卡片文字有没有被裁、录屏是否卡在无关画面、字幕有没有压在关键区域、有没有大段静音。
**没抽帧看过，不许说"做好了"。**

### Step 7 · 交付

一次给齐：`final.mp4` + `report.json` + `subtitles.srt` + `<EP>_台词稿.md` + `plan.csv` + `讲义.pptx`。
说明规格、字幕计时方式、哪些实拍是压速的、哪些功能"还没拍"。

---

## 铁律

1. **先台词后画面**。没有台词就不知道卡片停多久、录屏压几倍。
2. **时长以 ffprobe 实测为准**。`ffmpeg -t N` 出来的片段会比 N 少 1–3 帧，segment 的 `end` 必须用实测值，否则渲染报"片段范围越界"。
3. **`config.json` 里的路径相对 config 所在目录**。录屏在 `build/` 之外时用 `os.path.relpath`，不是相对项目根。
4. **卡片必须有 SVG 源**。只留 PNG 等于锁死文案，改一个字就要重画。
5. **原片只读**。剪辑点写在 `beats.json`，不改、不覆盖、不删录制文件。
6. **不许虚构实拍**。没录到的功能不念、不放进对照表；要么补录，要么台词明说"下一集给你看"。
7. **配音缓存要认 `--force`**。改完台词忘了加，听到的是上一版。
8. **一个事实一个出处**。演示里出现的数据（字节数、页数、耗时）必须是这次真实跑出来的。

---

## 命令速查

| 目的 | 命令 |
|---|---|
| 建项目 | `python scripts/init_project.py --root <dir> --title "…" --episodes 6` |
| SVG→PNG | `python scripts/svg2png.py --svg-dir <dir> --out-dir <dir>` |
| PNG→PPT | `python scripts/svg2pptx.py --png-dir <dir> --out x.pptx --beats beats.json` |
| 录屏 | `python scripts/record_window.py --title "Edge" --out rec/a.mp4 --stop-file build/stop` |
| 列窗口 | `python scripts/record_window.py --list` |
| 构建 | `python scripts/build_film.py --ep <集目录> [--subs] [--fit stretch] [--force]` |
| 出片 | `python scripts/build_film.py --ep <集目录> --render [--subs]` |
| 单源探测 | `python scripts/video_pipeline.py --ffmpeg <ff> probe <src.mp4>` |
| 抽帧 | `python scripts/video_pipeline.py --ffmpeg <ff> frames <src.mp4> --output <dir> --interval 2` |

Python 用隔离解释器；`--ffmpeg/--ffprobe` 默认 `C:/ffmpeg/bin/*.exe`，本机不是这个位置要显式传。

---

## 排错

| 现象 | 原因与处理 |
|---|---|
| PNG 出来 1080×608 之类怪尺寸 | 缺 `--force-device-scale-factor=1`，用 `svg2png.py` 走，别手敲命令 |
| 中文字体变方块 | SVG 里 `font-family` 加 `Microsoft YaHei` 兜底；本机无思源则删掉 Source Han |
| 渲染报"片段范围越界" | segment `end` 用了设定值而非实测时长；重跑 `build_film.py` 会自动测 |
| 渲染报"找不到 source" | 路径相对 `config.json` 目录写错；检查 `build/config.json` |
| 配音和字幕对不上 | 改了台词没 `--force`，旧 wav 还在缓存 |
| 某段静音 | `audio_mode=replace` 下每段必须有 `voice_file`；纯画面段 text 留空会自动补静音 |
| 成片整体偏小声 | 检查 `loudnorm` 是否被改；目标 `I=-16 LUFS`，`TP=-1.5` |
| PPT 里字改不了 | 设计如此：PPT 是整页图片，改字改 SVG 再重导 |

更多背景见 `references/`：`讲义卡规范.md`、`浏览器录制.md`、`配音与字幕.md`、`渲染配置.md`。
