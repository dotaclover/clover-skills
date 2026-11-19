# -*- coding: utf-8 -*-
"""把 AI 出的一图流九宫格/多宫格拼版切成单格。

一图流卡片（3x3 或 2x3）是一次调用出多张的标准做法，中文标题由 PIL 后期叠，
格内不写中文。切图时按实测缝隙裁掉拼版边界，再放大到目标画幅。

缝的位置因模型出图而异，先用 --probe 或肉眼量，再用 --seams 指定：
  python grid_cut.py grid.png --grid 3x3 --seams-x 1078,2156 --seams-y 1916
竖缝给 x 坐标列表（每个缝的中心），横缝给 y 坐标列表。

用法：
  # 2x2 两格横排（海报两格版）：竖缝在图中线
  python grid_cut.py poster.png --grid 2x2 --seams-x 1085 --seams-y 1920 \
      --cells 1,2,3 --target 1080x1920 --out cells/
  # 3x3 九宫格
  python grid_cut.py grid.png --grid 3x3 --seams-x 1078,2156 --seams-y 1916,3832 \
      --target 1080x1920 --out cells/
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("image")
    ap.add_argument("--grid", default="3x3", help="列x行，如 3x3 / 2x2")
    ap.add_argument("--seams-x", default="", help="竖缝 x 中心，逗号分隔")
    ap.add_argument("--seams-y", default="", help="横缝 y 中心，逗号分隔")
    ap.add_argument("--cells", default="", help="只导出这些格号（1 起，从左到右从上到下）")
    ap.add_argument("--target", default="1080x1920", help="每格输出尺寸")
    ap.add_argument("--gap", type=int, default=5, help="缝两侧各避让像素")
    ap.add_argument("--out", default="cells")
    a = ap.parse_args()

    im = Image.open(a.image).convert("RGB")
    w, h = im.size
    cols, rows = (int(x) for x in a.grid.lower().split("x"))
    sx = [int(x) for x in a.seams_x.split(",") if x] if a.seams_x else []
    sy = [int(x) for x in a.seams_y.split(",") if x] if a.seams_y else []
    want = set(int(x) for x in a.cells.split(",") if x) if a.cells else None
    tw, th = (int(x) for x in a.target.lower().split("x"))

    # 由缝中心构造每列的左右边界
    xs = [0] + sx + [w]
    ys = [0] + sy + [h]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    n = 0
    for r in range(rows):
        for c in range(cols):
            n += 1
            if want and n not in want:
                continue
            left = xs[c] + (a.gap if c > 0 else 0)
            right = xs[c + 1] - (a.gap if c < cols - 1 else 0)
            top = ys[r] + (a.gap if r > 0 else 0)
            bottom = ys[r + 1] - (a.gap if r < rows - 1 else 0)
            cell = im.crop((left, top, right, bottom)).resize((tw, th), Image.LANCZOS)
            p = out / f"cell{n}.jpg"
            cell.save(p, quality=95)
            print(n, (left, top, right, bottom), cell.size, "->", p)


if __name__ == "__main__":
    main()
