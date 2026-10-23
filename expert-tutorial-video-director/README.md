# 教程片厂 · 系列教程视频导演

给一个主题，出一套能看的教程视频：分集大纲 → 分镜台词 → SVG 讲义卡与 PPT → 真实操作录屏 → 配音 → 字幕 → 成片。

## 类型

Agent 型（单个 AI 专家），内置三个单一职责技能。

## 三个技能怎么分工

| 技能 | 管什么 | 能单独用吗 |
|---|---|---|
| `tutorial-series-plan` | 立项、分集、分镜台词，产出 `series.json` / `beats.json`。纯文字，不碰素材 | 能（只要大纲/脚本） |
| `svg-lecture-deck` | SVG 卡设计 + 渲染 PNG + 导 PPTX，任意画布 | 能（只要一份能改字的 PPT） |
| `tutorial-video-assemble` | 录屏、配音、字幕、剪辑出片，吃 `beats.json` | 能（只要把素材剪成片） |

共享契约只有一个：`beats.json`。字段定义在 `tutorial-video-assemble/references/beats契约.md`（唯一权威，改字段先改那里再改脚本）。

## 画布

不锁 1920×1080。`u = min(宽,高)/1080`，字号、边距、线宽全部乘 `u`：

| preset | 尺寸 | 用在 | PPT |
|---|---|---|---|
| `16:9` | 1920×1080 | 横屏教程（默认） | 13.33×7.5 in |
| `9:16` | 1080×1920 | 抖音 / 视频号 | 7.5×13.33 in |
| `1:1` | 1440×1440 | 方图 | 10×10 in |
| `4:5` | 1440×1800 | 小红书 | 10×12.5 in |
| `3:4` | 1080×1440 | 平板 / 投屏 | 7.5×10 in |
| `4k` | 3840×2160 | 大屏母版 | 26.67×15 in |

16:9 时 `u = 1`，和旧版逐像素一致。换画布不是缩放：竖屏要重排卡片、台词减字、实拍重录。

## 依赖

- 本机 `ffmpeg` / `ffprobe`（默认 `C:/ffmpeg/bin/`，可传参覆盖）
- Python：`edge-tts`（配音）、`python-pptx` + `Pillow`（导 PPT）
- Windows + Edge/Chrome（SVG 渲染、窗口录屏）

## 使用示例

- 我要做一套关于「用 AI 把活干完」的系列教程，先出分集大纲和第一集分镜
- 把这集讲稿做成竖屏 SVG 讲义卡，再导出一份竖屏 PPT
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
