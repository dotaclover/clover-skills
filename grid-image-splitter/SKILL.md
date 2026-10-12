---
name: grid-image-splitter
description: 宫格拼图切分工具。把九宫格/宫格图片（AI 生成的表情包九宫格、拼图等）快速切成多张小图。支持 2、4、6、8、9、16 宫格及任意 行x列 网格，支持自动识别宫格数。当用户要求"切九宫格""切成小图""split grid image""拆分拼图"时使用。
agent_created: true
---

# Grid Image Splitter（宫格图片切分）

将一张宫格拼图（如九宫格头像包）切成独立小图。

## 使用方法

运行脚本（依赖 Pillow，缺失时先 `pip install pillow`）：

```bash
python scripts/split_grid.py <图片路径> [-g 宫格数] [-o 输出目录] [-f png|jpg|webp]
```

### 参数

| 参数 | 说明 | 默认 |
|---|---|---|
| `image` | 输入图片路径（必填） | — |
| `-g, --grid` | 宫格数：`2`/`4`/`6`/`8`/`9`/`16`，或 `行x列`（如 `3x2`），或 `auto` | `auto` |
| `-o, --out` | 输出目录 | `<图名>_split/`（图片同目录下） |
| `-f, --format` | 输出格式 `png` / `jpg` / `webp` | `png` |

### 宫格预设对照

| 数量 | 网格 | 典型场景 |
|---|---|---|
| 2 | 1x2 | 左右双图 |
| 4 | 2x2 | 四宫格 |
| 6 | 2x3 | 横版六宫格 |
| 8 | 2x4 | 横版八宫格 |
| 9 | 3x3 | 九宫格头像包（最常用） |
| 16 | 4x4 | 十六宫格 |

### 自动识别规则（auto）

- 接近正方形（宽高比 0.85~1.15）→ 3x3
- 宽高比 >1.3 → 2x3；>2.0 → 1x4
- 宽高比 <0.77 → 3x2；<0.5 → 4x1
- 其余 → 2x2

## 执行步骤（Agent 使用）

1. 用 `-g auto` 或按用户指定的数量运行脚本。
2. 脚本输出切分结果路径列表，按"从左到右、从上到下"编号 `1.png`、`2.png`…。
3. 用 present_files 把所有小图展示给用户。

## 示例

```bash
# 九宫格（最常见）
python scripts/split_grid.py 微信图片.jpg -g 9

# 十六宫格，输出 jpg
python scripts/split_grid.py collage.png -g 16 -f jpg

# 任意 3 行 2 列
python scripts/split_grid.py photo.jpg -g 3x2
```
