"""九宫格/宫格图片切分工具：把一张宫格拼图切成 N 张小图。

用法:
    python split_grid.py <图片路径> [选项]

常用示例:
    # 自动识别宫格数（默认）
    python split_grid.py photo.jpg

    # 指定切 9 宫格 (3x3)
    python split_grid.py photo.jpg -g 9

    # 支持的预设: 2(1x2) 4(2x2) 6(2x3) 8(2x4) 9(3x3) 16(4x4)
    python split_grid.py photo.jpg -g 6

    # 显式指定行列（任意网格）
    python split_grid.py photo.jpg -g 3x2

    # 指定输出目录和格式
    python split_grid.py photo.jpg -g 9 -o out_dir -f jpg

依赖: pip install pillow
"""
import argparse
import os
import sys

from PIL import Image

# 预设: 数量 -> (行, 列)
PRESETS = {
    2: (1, 2),
    4: (2, 2),
    6: (2, 3),
    8: (2, 4),
    9: (3, 3),
    16: (4, 4),
}


def parse_grid(value: str):
    """解析 -g 参数: 支持 '9' / '3x3' / '3X3'"""
    v = value.strip().lower()
    if v in ("auto", ""):
        return None
    if "x" in v:
        rows, cols = v.split("x", 1)
        return int(rows), int(cols)
    n = int(v)
    if n not in PRESETS:
        raise ValueError(f"不支持的宫格数 {n}，可选: {sorted(PRESETS)} 或用 '行x列' 格式")
    return PRESETS[n]


def auto_grid(w: int, h: int) -> tuple:
    """根据宽高比自动猜测行列。正方形图默认 3x3。"""
    ratio = w / h
    if abs(ratio - 1.0) < 0.15:
        return (3, 3)  # 正方形 → 九宫格
    if ratio > 2.0:
        return (1, 4)  # 长条横图
    if ratio > 1.3:
        return (2, 3)  # 横向六宫格
    if ratio < 0.5:
        return (4, 1)
    if ratio < 0.77:
        return (3, 2)
    return (2, 2)


def main():
    ap = argparse.ArgumentParser(description="宫格图片切分工具")
    ap.add_argument("image", help="输入图片路径")
    ap.add_argument("-g", "--grid", default="auto",
                    help="宫格数: 2/4/6/8/9/16 或 '行x列'（如 3x3），默认 auto 自动识别")
    ap.add_argument("-o", "--out", default=None,
                    help="输出目录，默认为图片同目录下 <图名>_split/")
    ap.add_argument("-f", "--format", default="png", choices=["png", "jpg", "webp"],
                    help="输出格式，默认 png")
    args = ap.parse_args()

    if not os.path.isfile(args.image):
        sys.exit(f"文件不存在: {args.image}")

    try:
        grid = parse_grid(args.grid)
    except ValueError as e:
        sys.exit(str(e))

    im = Image.open(args.image)
    w, h = im.size
    if grid is None:
        grid = auto_grid(w, h)
    rows, cols = grid

    out_dir = args.out or os.path.join(
        os.path.dirname(os.path.abspath(args.image)),
        os.path.splitext(os.path.basename(args.image))[0] + "_split",
    )
    os.makedirs(out_dir, exist_ok=True)

    ext = "jpg" if args.format == "jpg" else args.format
    saved = []
    for r in range(rows):
        for c in range(cols):
            box = (c * w // cols, r * h // rows, (c + 1) * w // cols, (r + 1) * h // rows)
            tile = im.crop(box)
            n = r * cols + c + 1
            path = os.path.join(out_dir, f"{n}.{ext}")
            if ext == "jpg":
                tile = tile.convert("RGB")
            tile.save(path)
            saved.append(path)

    print(f"原图: {w}x{h}, 切分为 {rows}行x{cols}列 共 {rows*cols} 张")
    print(f"输出目录: {out_dir}")
    for p in saved:
        print(p)


if __name__ == "__main__":
    main()
