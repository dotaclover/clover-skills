---
name: svg-lecture-deck
description: Design lecture-card slide decks as hand-editable SVG at any canvas (16:9, 9:16 portrait, 1:1, 4:5, 4K), render them to PNG with a headless browser, and export a full-bleed PPTX with narration in the speaker notes. Use when the user wants course slides, 讲义卡, a deck for a video, or needs SVG rendered to PNG/PPTX.
agent_created: true
---

# SVG 讲义卡与 PPT

一套 SVG 源，两个出口：**喂视频**（PNG 静帧）和**给人看**（PPTX）。因为只有一份源，视频和 PPT 永远不会变成两个版本。

不做视频也能单独用：只要一份能改字的讲义 PPT，走这里就够了。

## 画布不是固定的

`scripts/canvas.py` 管预设和尺寸令牌：

| preset | 尺寸 | 用在 |
|---|---|---|
| `16:9` | 1920×1080 | 横屏教程、B 站 / YouTube（默认） |
| `9:16` | 1080×1920 | 竖屏短视频、抖音 / 视频号 |
| `1:1` | 1440×1440 | 方图 |
| `4:5` | 1440×1800 | 小红书 / Instagram |
| `3:4` | 1080×1440 | 平板 / 文档投屏 |
| `4k` | 3840×2160 | 大屏、二次剪辑母版 |
| 自定义 | `--size 1440x1080` | 任意，宽高必须偶数 |

**令牌规则**：`u = min(宽, 高) / 1080`，所有字号、边距、线宽都乘 `u`。
1920×1080 时 `u = 1`，和以前逐像素一致；4K 自动翻倍；竖屏 `u = 1` 但画布窄了，所以**文案要写短**（见 `references/画布与版式.md`）。

```bash
python scripts/canvas.py              # 打印所有预设的令牌与 PPT 尺寸
python scripts/canvas.py 1080x1920    # 看自定义画布
```

PPT 尺寸按 144 px = 1 in 换算：1920×1080 → 13.33×7.5（标准 16:9 幻灯片），1080×1920 → 7.5×13.33（竖版），1440×1440 → 10×10（方版）。不用手填。

## 流程

### 1. 先定版式，再写 SVG

一屏一个论点。出现第二个论点就拆卡。五种常用版式（片头 / 单概念 / 流程 / 对照 / 作业黑板）的骨架在 `references/画布与版式.md`，直接抄。

字号只用令牌里的档位，不要临时拍一个 52px 出来：

```bash
python -c "import canvas;print(canvas.tokens(1080,1920))"
```

### 2. 写 SVG

```svg
<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1920" viewBox="0 0 1080 1920">
```

- `width/height/viewBox` 三处必须一致，否则渲染出来会裁。
- 字体栈统一 `Source Han Sans SC, Microsoft YaHei, PingFang SC, sans-serif`，本机没思源会自动落雅黑。
- 色板、四叶草标记、间距规范见 `references/视觉规范.md`。
- 文件名带序号：`C01_片头.svg`、`C03b_三个拎清.svg`。

### 3. 渲染 PNG

```bash
python scripts/svg2png.py --svg-dir cards --preset 9:16
python scripts/svg2png.py --file a.svg --size 1440x1080 --scale 2
python scripts/svg2png.py --check          # 只检查浏览器
```

默认输出到同级 `<目录名>_png/`。

### 4. 导 PPT

```bash
python scripts/svg2pptx.py --png-dir cards_png --out out/讲义.pptx --beats beats.json
python scripts/svg2pptx.py --svg-dir cards --preset 9:16 --out out/讲义.pptx   # 顺带渲 PNG
```

`--beats` 会把每张卡对应的台词写进备注页，讲的时候照着念。

## 坑（都踩过）

| 现象 | 原因 |
|---|---|
| 输出 1080×608 之类怪尺寸 | 缺 `--force-device-scale-factor=1`。只准走 `svg2png.py`，别手敲 msedge |
| 画面被裁掉一块 | `--window-size` 和 SVG 的 `width/height` 不一致 |
| 中文变方块 | `font-family` 只写了思源，加 `Microsoft YaHei` 兜底 |
| 渲染出空白图 | 并发渲多张，改成串行（脚本已是串行） |
| PPT 里字改不了 | 设计如此：PPT 是整页图片，改字改 SVG 重导 |
| 竖屏文字被平台 UI 压住 | 正文别越过底部 25%，见版式规范的安全区 |

## 依赖

- Edge 或 Chrome（无头渲染 PNG）
- `python-pptx` + `Pillow`（导 PPT，见 `requirements.txt`）

## 校验

渲染完至少看一眼：文字有没有出安全区、有没有被换行挤掉、有没有缺字。
批量查尺寸：

```bash
for f in cards_png/*.png; do ffprobe -v error -select_streams v -show_entries stream=width,height -of csv=p=0 "$f"; done
```
