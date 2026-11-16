# -*- coding: utf-8 -*-
"""讲义卡 SVG -> PNG（Windows 无头浏览器批量渲染）。

用法：
    python svg2png.py --svg-dir cards/ --preset 16:9
    python svg2png.py --svg-dir cards/ --preset 9:16 --out-dir cards_png/
    python svg2png.py --file a.svg b.svg --size 1080x1920
    python svg2png.py --svg-dir cards/ --width 1440 --height 1440 --scale 2
    python svg2png.py --check              # 只检查浏览器是否可用

关键点（踩过的坑）：
1. 必须给 --force-device-scale-factor=1，否则输出是 1080×608 之类的怪尺寸。
2. --window-size 必须等于画布尺寸，否则按窗口裁切。
3. file:// URL 里的中文路径要 percent-encode（本脚本自动处理）。
4. 一次进程渲一张，串行执行；并发会偶发截到空白帧。
"""
import argparse
import subprocess
import sys
import tempfile
import urllib.parse
from pathlib import Path

import canvas

CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]


def find_browser(explicit=None):
    if explicit:
        p = Path(explicit)
        if not p.exists():
            raise SystemExit("指定的浏览器不存在: %s" % explicit)
        return str(p)
    for c in CANDIDATES:
        if Path(c).exists():
            return c
    raise SystemExit("没找到 Edge/Chrome，请用 --browser 指定可执行文件路径")


def render(browser, svg: Path, out: Path, w: int, h: int, scale: int) -> bool:
    url = "file:///" + urllib.parse.quote(str(svg.resolve()).replace("\\", "/"))
    with tempfile.TemporaryDirectory() as td:
        cmd = [
            browser, "--headless=new", "--disable-gpu", "--hide-scrollbars",
            "--no-first-run", "--no-default-browser-check",
            "--force-device-scale-factor=%d" % scale,
            "--window-size=%d,%d" % (w, h),
            "--user-data-dir=" + td,
            "--screenshot=" + str(out.resolve()),
            url,
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if not out.exists() or out.stat().st_size < 1024:
        print("  [X] %s 渲染失败: %s" % (svg.name, (r.stderr or "")[-300:]))
        return False
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--svg-dir")
    ap.add_argument("--file", nargs="*")
    ap.add_argument("--out-dir")
    ap.add_argument("--preset", help="16:9 / 9:16 / 1:1 / 4:5 / 3:4 / 4k")
    ap.add_argument("--size", help="宽x高，如 1080x1920")
    ap.add_argument("--width", type=int)
    ap.add_argument("--height", type=int)
    ap.add_argument("--scale", type=int, default=1, help="2 = 输出 2 倍图")
    ap.add_argument("--browser")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()

    browser = find_browser(a.browser)
    print("浏览器:", browser)
    if a.check:
        return 0

    if a.size:
        w, h = canvas.parse_size(a.size)
    elif a.width and a.height:
        w, h = canvas.resolve({"width": a.width, "height": a.height})
    else:
        w, h = canvas.resolve({"preset": a.preset or "16:9"})
    print("画布:", canvas.describe(w, h))

    files = []
    if a.svg_dir:
        files += sorted(Path(a.svg_dir).glob("*.svg"))
    if a.file:
        files += [Path(f) for f in a.file]
    if not files:
        print("没有找到 SVG，用 --svg-dir 或 --file 指定")
        return 1

    if a.out_dir:
        out_dir = Path(a.out_dir)
    elif a.svg_dir:
        out_dir = Path(a.svg_dir).resolve().parent / (Path(a.svg_dir).name + "_png")
    else:
        out_dir = files[0].resolve().parent / "png"
    out_dir.mkdir(parents=True, exist_ok=True)

    ok = 0
    for f in files:
        out = out_dir / (f.stem + ".png")
        if render(browser, f, out, w, h, a.scale):
            ok += 1
            print("  [OK] %s -> %s (%d KB)" % (f.name, out.name, out.stat().st_size // 1024))
    print("完成 %d/%d -> %s" % (ok, len(files), out_dir))
    return 0 if ok == len(files) else 2


if __name__ == "__main__":
    sys.exit(main())
