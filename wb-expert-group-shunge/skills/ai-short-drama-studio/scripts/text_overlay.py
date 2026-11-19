# -*- coding: utf-8 -*-
"""通用中文叠字：把一行/多行文字按铁律绘制成透明 PNG 叠字层。

中文一律 PIL 叠字，不让生图模型写中文。排版铁律：
- 数字与中文/字母紧挨，不加空格（写「第1天」不写「第 1 天」）
- `·` 两侧不留空格；英文词组内部空格保留
- 描边黑边保证压在亮画面上也读得清
- 居中必须按 getbbox(含描边) 量，不用 getlength（否则整行偏左）

用法：
  # 单行（金色数字、白色中文，按段指定颜色）
  python text_overlay.py out.png 720 1280 \
      --seg 第:white --seg 6:gold --seg 天:white
  # 居中单行纯文本
  python text_overlay.py out.png 720 1280 --text "第6天·08:55" --size 80 --y 148
  # 右下角水印
  python text_overlay.py out.png 720 1280 --text "@AI从零开始" --size 20 --y 1228 --anchor-x right --margin 16
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from common import FONT_BOLD, centered_x, draw_text_run

COLORS = {
    "white": (255, 255, 255),
    "gold": (255, 197, 61),
    "black": (0, 0, 0),
    "red": (235, 60, 60),
}


def color_of(s: str):
    if s.startswith("#"):
        return tuple(int(s[i:i + 2], 16) for i in (1, 3, 5))
    return COLORS.get(s, COLORS["white"])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("out", help="输出 PNG 路径")
    ap.add_argument("width", type=int)
    ap.add_argument("height", type=int)
    ap.add_argument("--seg", action="append", default=[],
                    help="一段文字，格式 文本:颜色（颜色 white/gold/black/red 或 #RRGGBB）")
    ap.add_argument("--text", help="整行纯文本（与 --seg 二选一）")
    ap.add_argument("--size", type=int, default=80, help="字号（--text 模式）")
    ap.add_argument("--color", default="white", help="--text 模式颜色")
    ap.add_argument("--bold", action="store_true", default=True)
    ap.add_argument("--y", type=int, default=None, help="基线 y（默认垂直居中）")
    ap.add_argument("--stroke", type=int, default=7)
    ap.add_argument("--anchor-x", choices=["center", "left", "right"], default="center")
    ap.add_argument("--margin", type=int, default=16, help="right 锚点时的右边距")
    a = ap.parse_args()

    font_path = FONT_BOLD if a.bold else FONT_BOLD
    if a.seg:
        parts = []
        for item in a.seg:
            text, _, col = item.rpartition(":")
            if not text:  # 没写颜色
                text, col = item, "white"
            parts.append((text, ImageFont.truetype(font_path, a.size), color_of(col)))
    else:
        text = a.text or ""
        parts = [(text, ImageFont.truetype(font_path, a.size), color_of(a.color))]

    img = Image.new("RGBA", (a.width, a.height), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    y = a.y if a.y is not None else (a.height - a.size) // 2
    if a.anchor_x == "center":
        x = centered_x(a.width, parts, stroke=a.stroke)
    elif a.anchor_x == "left":
        x = a.margin
    else:
        total = sum(f.getlength(s) for s, f, _ in parts)
        x = a.width - a.margin - total
    draw_text_run(d, x, y, parts, stroke=a.stroke)

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    print(out, img.size)


if __name__ == "__main__":
    main()
