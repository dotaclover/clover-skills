# -*- coding: utf-8 -*-
"""讲义卡 -> PPTX（每张卡一页，满屏，台词写进备注）。

用法：
    python svg2pptx.py --png-dir cards_png --out out/讲义.pptx --beats beats.json
    python svg2pptx.py --svg-dir cards --preset 9:16 --out out/讲义.pptx   # 自动先渲 PNG

说明：
- 卡片由 SVG 生成，PPT 里是整页图片，字不能在 PPT 里改。这是有意的：
  一份源（SVG）同时喂视频和 PPT，两边永远不走形。要改字改 SVG 再重导。
- 幻灯片尺寸按图片比例自动定（144 px = 1 in）：1920×1080→13.33×7.5 标准 16:9，
  1080×1920→7.5×13.33 竖版，1440×1440→10×10 方版。
- 传 --beats 时按 png 文件名把该段台词写进备注页，方便照着讲。
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import canvas


def image_size(p):
    try:
        from PIL import Image
        with Image.open(p) as im:
            return im.size
    except ImportError:
        raise SystemExit("需要 Pillow 读图尺寸：pip install pillow")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--png-dir")
    ap.add_argument("--svg-dir")
    ap.add_argument("--preset", default="16:9")
    ap.add_argument("--out", required=True)
    ap.add_argument("--beats")
    ap.add_argument("--browser")
    a = ap.parse_args()

    png_dir = Path(a.png_dir) if a.png_dir else None
    if not png_dir and a.svg_dir:
        png_dir = Path(a.svg_dir) / "png"
        cmd = [sys.executable, str(Path(__file__).with_name("svg2png.py")),
               "--svg-dir", a.svg_dir, "--out-dir", str(png_dir),
               "--preset", a.preset]
        if a.browser:
            cmd += ["--browser", a.browser]
        subprocess.run(cmd, check=True)
    if not png_dir or not png_dir.exists():
        print("需要 --png-dir 或 --svg-dir")
        return 1

    pngs = sorted(png_dir.glob("*.png"))
    if not pngs:
        print("目录里没有 PNG:", png_dir)
        return 1

    notes = {}
    if a.beats:
        d = json.loads(Path(a.beats).read_text(encoding="utf-8"))
        for b in d.get("beats", []):
            if b.get("kind") == "card" and b.get("png"):
                notes[Path(b["png"]).stem] = b.get("text", "")

    w, h = image_size(pngs[0])
    win, hin = canvas.slide_inches(w, h)
    print("图片 %d×%d -> 幻灯片 %.2f×%.2f in" % (w, h, win, hin))

    from pptx import Presentation
    from pptx.util import Inches

    prs = Presentation()
    prs.slide_width = Inches(win)
    prs.slide_height = Inches(hin)
    blank = prs.slide_layouts[6]

    for p in pngs:
        pw, ph = image_size(p)
        if (pw, ph) != (w, h):
            print("  [!] %s 尺寸 %d×%d 与其他卡不一致，会被拉伸" % (p.name, pw, ph))
        s = prs.slides.add_slide(blank)
        s.shapes.add_picture(str(p), 0, 0, width=prs.slide_width, height=prs.slide_height)
        txt = notes.get(p.stem, "")
        if txt:
            s.notes_slide.notes_text_frame.text = txt

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(out))
    print("已生成 PPT: %s（%d 页，%d KB）" % (out, len(pngs), out.stat().st_size // 1024))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
