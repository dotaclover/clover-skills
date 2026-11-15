# -*- coding: utf-8 -*-
"""量出录屏 / 截图里内容真正的边界，别靠肉眼猜裁切框。

    python measure_crop.py 录屏.mp4 --t 12
    python measure_crop.py 长图.png
    python measure_crop.py 录屏.mp4 --t 12 --y 300 1100   只看这段高度

输出：每 100px 一格的「墨迹量」（暗色文字像素数）。墨迹密集的连续区间就是内容，
稀疏或为 0 的地方是留白 / 面板间隙，可以作为裁切边界。
默认按 4:5（竖屏画面框 960x1200）给出一版建议裁切。
"""
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

RATIO = 0.8  # 960/1200


def load(path, t=None):
    if t is None:
        return Image.open(path).convert("L")
    tmp = Path(tempfile.gettempdir()) / "measure_crop.png"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(t), "-i", str(path),
                    "-frames:v", "1", str(tmp)], check=True)
    return Image.open(tmp).convert("L")


def zones(counts, step, thresh):
    """连续超过阈值的区间。"""
    out, start = [], None
    for i, c in enumerate(counts):
        if c > thresh and start is None:
            start = i
        elif c <= thresh and start is not None:
            out.append((start * step, i * step))
            start = None
    if start is not None:
        out.append((start * step, len(counts) * step))
    return out


def suggest(x0, x1, w, h):
    """以内容区间为中心，给一版 4:5 裁切。"""
    cw = min(max(x1 - x0 + 120, 900), int(h * RATIO))
    ch = int(cw / RATIO)
    cx = (x0 + x1) // 2 - cw // 2
    cx = max(0, min(cx, w - cw))
    return cw, ch, cx, max(0, (h - ch) // 2)


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return
    path = args[0]
    t = args[args.index("--t") + 1] if "--t" in args else None
    img = load(path, t)
    a = np.asarray(img).astype(int)
    h, w = a.shape
    y0, y1 = (int(args[args.index("--y") + 1]), int(args[args.index("--y") + 2])) \
        if "--y" in args else (0, h)

    ink = a < 160
    step = 100
    cs = [(x, int(ink[y0:y1, x:x + step].sum())) for x in range(0, w, step)]
    rs = [(y, int(ink[y:y + step, :].sum())) for y in range(0, h, step)]

    print(f"{w}x{h}  观察高度 {y0}-{y1}")
    print("列:", " ".join(f"{x}:{c}" for x, c in cs))
    print("行:", " ".join(f"{y}:{c}" for y, c in rs))

    col_max = max(c for _, c in cs) or 1
    zs = [z for z in zones([c for _, c in cs], step, col_max * 0.06) if z[1] - z[0] >= 200]
    print("列墨迹区间:", zs)
    if zs:
        x0, x1 = zs[0][0], zs[-1][1]
        cw, ch, cx, cy = suggest(x0, x1, w, h)
        print(f"建议 vcrop: ({cx}, {cy}, {cw}, {ch})  —— 4:5，覆盖 {x0}-{x1}")


if __name__ == "__main__":
    main()
