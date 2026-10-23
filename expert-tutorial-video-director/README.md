# 教程片厂 · 系列教程视频导演

给一个主题，出一套能看的教程视频：分集大纲 → 分镜台词 → SVG 讲义卡与 PPT → 真实操作录屏 → 配音 → 字幕 → 成片。

## 类型

Agent 型（单个 AI 专家），内置技能 `tutorial-video-pipeline`。

## 功能

| 阶段 | 干什么 | 主要产物 |
|---|---|---|
| 立项 | 主题拆集，定受众与固定开头结尾 | `series.json` |
| 分镜 | 每集写成 card/demo 交替的 beats | `beats.json` |
| 讲义卡 | 1920×1080 SVG，一套源喂视频和 PPT | `cards/*.svg`、`cards_png/*.png`、`讲义.pptx` |
| 实拍 | 按窗口标题 ffmpeg 录屏，优雅收尾 | `rec/*.mp4` |
| 配音 | edge-tts 逐段合成 + -16 LUFS 归一 | `build/audio/*.wav` |
| 出片 | 音频定节奏，字幕按句摊时，可选烧录 | `final.mp4`、`subtitles.srt`、`report.json` |
| 交付 | 台词稿、分镜表、验收记录 | `<EP>_台词稿.md`、`plan.csv` |

内置脚本（`skills/tutorial-video-pipeline/scripts/`）：

- `init_project.py` 建项目骨架
- `svg2png.py` SVG → PNG（Edge 无头，避开缩放坑）
- `svg2pptx.py` PNG → 16:9 PPTX（台词进备注）
- `record_window.py` 按窗口录屏，`--stop-file` 收尾
- `build_film.py` 配音 + 卡片片段 + 配置 + 字幕，一条命令
- `video_pipeline.py` 配置驱动渲染器

## 依赖

- 本机 `ffmpeg` / `ffprobe`（默认 `C:/ffmpeg/bin/`，可传参覆盖）
- Python：`edge-tts`、`python-pptx`（见 `skills/tutorial-video-pipeline/requirements.txt`）
- Windows + Edge/Chrome（SVG 渲染、窗口录屏）

## 使用示例

- 我要做一套关于「用 AI 把活干完」的系列教程，先出分集大纲和第一集分镜
- 把这集讲稿做成 SVG 讲义卡，再导出一份 PPT
- 录一段这个浏览器操作，配 edge-tts 配音和字幕，剪成成片

## 明确不做

- 不虚构实拍：没录到的功能不念、不放进对照表
- 不编数据：演示里的字节数、页数、耗时必须是真跑出来的
- PPT 里是整页图片，改字要改 SVG 重导（有意为之：视频和 PPT 永远是同一份源）

## 头像

`avatars/tutorial-video-director.png`，512×512。替换要求：PNG/JPG，512×512，≤500KB。

## 打包分享

```bash
python3 <skills>/expert-manager/scripts/package_expert.py <expert-dir>
```
