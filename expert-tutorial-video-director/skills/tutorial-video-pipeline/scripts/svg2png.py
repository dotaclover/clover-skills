# -*- coding: utf-8 -*-
"""讲义卡 SVG -> PNG（Windows 无头浏览器批量渲染）。

用法：
    python svg2png.py --svg-dir <SVG目录> [--out-dir <PNG目录>] [--width 1920] [--height 1080]
    python svg2png.py --file a.svg b.svg --out-dir png/
    python svg2png.py --svg-dir cards/ --check      # 只检查浏览器是否可用

关键点（踩过的坑）：
1. 必须给 --force-device-scale-factor=1，否则输出是 1080×608 之类的怪尺寸。
2. --window-size 必须等于画布尺寸，否则按窗口裁切。
3. file:// URL 里的中文路径要 percent-encode（本脚本自动处理）。
4. 每次启动进程渲染一张，串行执行；并发会偶发截到空白帧。
"""
import argparse
import subprocess
import sys
import tempfile
import urllib.parse
from pathlib import Path

CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]


def find_browser(explicit=None):
    if explicit:
        p = Path(explicit)
        if p.exists():
            return str(p)
        raise SystemExit("指定的浏览器不存在: %s" % explicit)
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
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    ap.add_argument("--scale", type=int, default=1, help="2 = 输出 2 倍图（3840×2160）")
    ap.add_argument("--browser")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()

    browser = find_browser(a.browser)
    print("浏览器:", browser)
    if a.check:
        return 0

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
        if render(browser, f, out, a.width, a.height, a.scale):
            ok += 1
            print("  [OK] %s -> %s (%d KB)" % (f.name, out.name, out.stat().st_size // 1024))
    print("完成 %d/%d -> %s" % (ok, len(files), out_dir))
    return 0 if ok == len(files) else 2


if __name__ == "__main__":
    sys.exit(main())
