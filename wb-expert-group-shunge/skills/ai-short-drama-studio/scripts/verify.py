# -*- coding: utf-8 -*-
"""成片抽帧验收：解流、静音段核对、切换点三帧拼图、近白像素检测。

验收铁律：
- 换日黑场点必须抽「点前 0.10s / 点后 0.10s / 点后 0.45s」三帧确认真的切黑。
- 台词静音区必须抽帧确认字幕层也消失（音轨静音 ≠ 字幕删掉）。
- 模型把台词画进画面（白色字幕）时，用两条片同秒位抽帧 + 近白像素量对比，
  不要用 -ss 帧和 fps=24 序列帧拼校对图（帧号会差一帧）。

用法：
  # 基本信息 + 静音段
  python verify.py final.mp4 --info
  # 切换点三帧拼图（黑场/字幕核对）
  python verify.py final.mp4 --joints 32.458 43.388 73.874 --out verify/
  # 单秒位抽帧
  python verify.py final.mp4 --frame 16.5 --out shot.png
  # 近白像素计数（检测画面里被模型画出的白字）
  python verify.py final.mp4 --frame 28.5 --near-white --threshold 235
"""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from common import FONT_BOLD, duration, ff, probe_size, silences

OFFSETS = (-0.10, 0.10, 0.45)


def lum(p: Path) -> float:
    im = Image.open(p).convert("L").resize((72, 128))
    px = list(im.getdata())
    return sum(px) / len(px)


def near_white(p: Path, threshold: int) -> int:
    im = Image.open(p).convert("RGB")
    n = 0
    for r, g, b in im.getdata():
        if r >= threshold and g >= threshold and b >= threshold:
            n += 1
    return n


def extract(video: Path, t: float, out: Path) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    ff(["ffmpeg", "-v", "error", "-ss", f"{max(0.0, t):.3f}",
        "-i", str(video), "-frames:v", "1", "-y", str(out)])
    return out


def joints_sheet(video: Path, times: list[float], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for t in times:
        trio = []
        for off in OFFSETS:
            p = extract(video, t + off, out_dir / f"{t:08.3f}_{off:+.2f}.jpg")
            trio.append((p, lum(p)))
        rows.append((t, trio))
    cw, ch, gap = 190, 338, 8
    w = 3 * cw + 40
    h = 26 + len(rows) * (ch + 30)
    sheet = Image.new("RGB", (w, h), (16, 16, 18))
    d = ImageDraw.Draw(sheet)
    font = ImageFont.truetype(FONT_BOLD, 15)
    for r, (t, trio) in enumerate(rows):
        y = 26 + r * (ch + 30)
        d.text((6, y - 20), f"{t:.3f}s", font=font, fill=(255, 210, 60))
        for c, (p, l) in enumerate(trio):
            im = Image.open(p).convert("RGB").resize((cw, ch), Image.LANCZOS)
            sheet.paste(im, (6 + c * (cw + gap), y))
            d.text((6 + c * (cw + gap) + 3, y + 3), f"L{l:.0f}",
                   font=font, fill=(0, 255, 120))
    out = out_dir / "_joints.jpg"
    sheet.save(out, quality=92, subsampling=0)
    print("拼图", out, sheet.size)
    for t, trio in rows:
        print("  %.3fs -> L值 %s" % (t, [f"{l:.0f}" for _, l in trio]))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("video")
    ap.add_argument("--info", action="store_true")
    ap.add_argument("--silence", action="store_true")
    ap.add_argument("--joints", nargs="*", type=float)
    ap.add_argument("--frame", type=float)
    ap.add_argument("--near-white", action="store_true")
    ap.add_argument("--threshold", type=int, default=235)
    ap.add_argument("--out", default="verify")
    a = ap.parse_args()

    v = Path(a.video)
    if a.info:
        w, h = probe_size(v)
        print(f"{v.name}: {duration(v):.3f}s, {w}x{h}")
    if a.silence:
        sil = silences(v)
        print(f"静音段 {len(sil)} 处：")
        for s, e in sil:
            print(f"  {s:7.3f} — {e:7.3f}  ({e-s:.3f}s)")
    if a.joints:
        joints_sheet(v, a.joints, Path(a.out))
    if a.frame is not None:
        p = extract(v, a.frame, Path(a.out) / f"f{a.frame:.3f}.png")
        print("抽帧", p)
        if a.near_white:
            print("  近白像素", near_white(p, a.threshold))


if __name__ == "__main__":
    main()
