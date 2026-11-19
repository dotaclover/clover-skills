# -*- coding: utf-8 -*-
"""换日计数器叠字卡：顶部软渐变 + 「第N天·HH:MM」，天数逐镜递增。

把「每天早一分钟」直接写在画面上，是过渡蒙太奇的关键道具。
排版铁律：数字与中文紧挨不加空格；`·` 两侧不留空格。
居中按包围盒量（见 common.centered_x），不能按 getlength 累加。

用法：
  # 默认：第1天09:00 起每天早一分钟，生成第1/6/16/30天
  python day_card.py --out-dir cards/ --days 1 6 16 30
  # 自定义起点时间（如 08:59 起）
  python day_card.py --out-dir cards/ --days 1 2 3 --start 08:59 --size 720x1280
  # 入职前一夜写「前1天」
  python day_card.py --out-dir cards/ --days 0
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from common import FONT_BOLD, centered_x, draw_text_run

WHITE = (255, 255, 255)
GOLD = (255, 197, 61)


def day_time(day: int, start_min: int) -> str:
    """第 N 天应到时间 = 起点减去 (N-1) 分钟。"""
    total = start_min - (day - 1)
    return "%02d:%02d" % (total // 60, total % 60)


def build(day: int, out: Path, w: int, h: int, start_min: int,
          f_cn: int, f_num: int, f_time: int, baseline: int,
          grad_h: int, grad_a: int, stroke: int) -> Path:
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    grad = Image.new("RGBA", (w, grad_h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    for y in range(grad_h):
        a = int(grad_a * (1 - y / grad_h) ** 1.6)
        gd.rectangle([0, y, w, y + 1], fill=(0, 0, 0, a))
    img.alpha_composite(grad, (0, 0))

    fc = ImageFont.truetype(FONT_BOLD, f_cn)
    fn = ImageFont.truetype(FONT_BOLD, f_num)
    ft = ImageFont.truetype(FONT_BOLD, f_time)
    if day == 0:
        parts = [("前", fc, WHITE), ("1", fn, GOLD), ("天", fc, WHITE)]
    else:
        parts = [("第", fc, WHITE), (str(day), fn, GOLD), ("天", fc, WHITE),
                 ("·", fc, WHITE), (day_time(day, start_min), ft, GOLD)]

    x = centered_x(w, parts, stroke=stroke)
    draw_text_run(ImageDraw.Draw(img), x, baseline, parts, stroke=stroke)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", default="cards")
    ap.add_argument("--days", nargs="+", type=int, default=[1, 6, 16, 30])
    ap.add_argument("--start", default="09:00", help="第1天应到时间 HH:MM")
    ap.add_argument("--size", default="720x1280")
    ap.add_argument("--f-cn", type=int, default=80)
    ap.add_argument("--f-num", type=int, default=98)
    ap.add_argument("--f-time", type=int, default=70)
    ap.add_argument("--baseline", type=int, default=148)
    ap.add_argument("--grad-h", type=int, default=300)
    ap.add_argument("--grad-a", type=int, default=132)
    ap.add_argument("--stroke", type=int, default=7)
    a = ap.parse_args()

    w, h = (int(x) for x in a.size.lower().split("x"))
    hh, mm = (int(x) for x in a.start.split(":"))
    start_min = hh * 60 + mm
    out_dir = Path(a.out_dir)
    for day in a.days:
        p = build(day, out_dir / f"day{day:02d}.png", w, h, start_min,
                  a.f_cn, a.f_num, a.f_time, a.baseline,
                  a.grad_h, a.grad_a, a.stroke)
        print(p, "" if day == 0 else day_time(day, start_min))


if __name__ == "__main__":
    main()
