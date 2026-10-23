# -*- coding: utf-8 -*-
"""讲义卡 -> PPTX（每张卡一页，满屏 16:9，台词写进备注）。

用法：
    python svg2pptx.py --png-dir <PNG目录> --out <输出.pptx> [--beats beats.json]
    python svg2pptx.py --svg-dir <SVG目录> --out deck.pptx    # 自动先渲染 PNG

说明：
- 卡片由 SVG 生成，PPT 里是整页图片，所以字不能在 PPT 里改；要改字改 SVG 再重导。
  这是有意的：一份源文件（SVG）同时喂视频和 PPT，两边不会走形。
- 传 --beats 时按 png 文件名把该段台词写进备注页，方便直接照着讲。
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

EMU_PER_IN = 914400
SLIDE_W = 13.3333
SLIDE_H = 7.5


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--png-dir")
    ap.add_argument("--svg-dir")
    ap.add_argument("--out", required=True)
    ap.add_argument("--beats")
    ap.add_argument("--browser")
    a = ap.parse_args()

    png_dir = Path(a.png_dir) if a.png_dir else None
    if not png_dir and a.svg_dir:
        png_dir = Path(a.svg_dir) / "png"
        cmd = [sys.executable, str(Path(__file__).with_name("svg2png.py")),
               "--svg-dir", a.svg_dir, "--out-dir", str(png_dir)]
        if a.browser:
            cmd += ["--browser", a.browser]
        subprocess.run(cmd, check=True)
    if not png_dir or not png_dir.exists():
        print("需要 --png-dir 或 --svg-dir")
        return 1

    pngs = sorted([p for p in png_dir.glob("*.png")])
    if not pngs:
        print("目录里没有 PNG:", png_dir)
        return 1

    notes = {}
    if a.beats:
        d = json.loads(Path(a.beats).read_text(encoding="utf-8"))
        for b in d.get("beats", []):
            if b.get("kind") == "card" and b.get("png"):
                notes[Path(b["png"]).stem] = b.get("text", "")

    from pptx import Presentation
    from pptx.util import Inches

    prs = Presentation()
    prs.slide_width = Inches(SLIDE_W)
    prs.slide_height = Inches(SLIDE_H)
    blank = prs.slide_layouts[6]

    for p in pngs:
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
