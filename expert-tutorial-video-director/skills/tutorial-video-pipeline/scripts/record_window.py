# -*- coding: utf-8 -*-
"""按窗口标题录屏（Windows / gdigrab），给"浏览器实拍"用。

用法：
    python record_window.py --list
    python record_window.py --title "Edge" --duration 60 --out rec/demo01.mp4
    python record_window.py --title "Edge" --out rec/demo01.mp4 --stop-file build/stop

说明：
- 只认可见顶层窗口，标题做包含匹配，不区分大小写。
- 录制前把窗口最大化并强制置前，画面里只有这一个应用；--no-max 保留原尺寸。
- gdigrab 只读像素，不接管键鼠，录制期间可以正常操作（也可以由脚本操作）。
- --stop-file：文件一出现就发 q 给 ffmpeg 收尾，避免直接 kill 导致末帧损坏。
  推荐用法：后台起录制（--duration 300 兜底），操作完 touch 这个文件。
"""
import argparse
import ctypes
import subprocess
import sys
import time
from ctypes import wintypes
from pathlib import Path

FFMPEG = r"C:/ffmpeg/bin/ffmpeg.exe"
SW_MAXIMIZE, SW_RESTORE = 3, 9
VK_MENU, KEYEVENTF_KEYUP = 0x12, 0x0002

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
user32.SetProcessDPIAware()
EnumProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


def iter_windows():
    found = []

    def cb(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        n = user32.GetWindowTextLengthW(hwnd)
        if n == 0:
            return True
        buf = ctypes.create_unicode_buffer(n + 1)
        user32.GetWindowTextW(hwnd, buf, n + 1)
        found.append((hwnd, buf.value))
        return True

    user32.EnumWindows(EnumProc(cb), 0)
    return found


def find_window(keyword):
    kw = keyword.lower()
    for hwnd, title in iter_windows():
        if kw in title.lower():
            return hwnd, title
    return None, None


def force_foreground(hwnd, maximize=True):
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, SW_RESTORE)
    if maximize:
        user32.ShowWindow(hwnd, SW_MAXIMIZE)
    fg = user32.GetForegroundWindow()
    t_fg = user32.GetWindowThreadProcessId(fg, None)
    t_me = kernel32.GetCurrentThreadId()
    attached = False
    if t_fg and t_fg != t_me:
        attached = bool(user32.AttachThreadInput(t_me, t_fg, True))
    user32.keybd_event(VK_MENU, 0, 0, 0)
    user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
    user32.BringWindowToTop(hwnd)
    user32.SetForegroundWindow(hwnd)
    user32.SetFocus(hwnd)
    if attached:
        user32.AttachThreadInput(t_me, t_fg, False)


def clamp_rect(hwnd):
    r = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    sw, sh = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    x, y = max(0, r.left), max(0, r.top)
    w = min(r.right, sw) - x
    h = min(r.bottom, sh) - y
    return x, y, max(16, w - w % 2), max(16, h - h % 2)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", help="窗口标题关键词")
    ap.add_argument("--list", action="store_true", help="列出可见窗口")
    ap.add_argument("--duration", type=float, default=60.0, help="最长录制秒数（兜底）")
    ap.add_argument("--out", help="输出 mp4")
    ap.add_argument("--stop-file", help="该文件出现即停")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--crf", type=int, default=18)
    ap.add_argument("--no-max", action="store_true", help="不最大化窗口")
    ap.add_argument("--draw-mouse", action="store_true", help="录制鼠标指针")
    ap.add_argument("--ffmpeg", default=FFMPEG)
    a = ap.parse_args()

    if a.list or not a.title:
        for hwnd, t in iter_windows():
            print("%-10s %s" % (hwnd, t))
        return 0 if a.list else 2
    if not a.out:
        print("需要 --out")
        return 2

    hwnd, title = find_window(a.title)
    if not hwnd:
        print("[X] 没找到标题含「%s」的可见窗口，用 --list 看看" % a.title)
        return 1
    print("[1] 命中窗口:", title)

    force_foreground(hwnd, maximize=not a.no_max)
    time.sleep(1.0)
    x, y, w, h = clamp_rect(hwnd)
    print("[2] 录制区域 %d,%d %dx%d，最长 %.0fs" % (x, y, w, h, a.duration))

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    stop = Path(a.stop_file) if a.stop_file else None
    if stop and stop.exists():
        stop.unlink()

    cmd = [a.ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
           "-f", "gdigrab", "-draw_mouse", "1" if a.draw_mouse else "0",
           "-framerate", str(a.fps), "-offset_x", str(x), "-offset_y", str(y),
           "-video_size", "%dx%d" % (w, h), "-i", "desktop",
           "-t", "%.2f" % a.duration,
           "-c:v", "libx264", "-preset", "ultrafast", "-crf", str(a.crf),
           "-pix_fmt", "yuv420p", str(out)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                         stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    t0 = time.time()
    try:
        while p.poll() is None:
            if stop and stop.exists():
                print("[3] 收到停止信号，收尾中 ...")
                p.stdin.write(b"q")
                p.stdin.flush()
                break
            if time.time() - t0 > a.duration + 5:
                p.stdin.write(b"q")
                p.stdin.flush()
                break
            time.sleep(0.2)
    finally:
        try:
            p.stdin.close()
        except Exception:
            pass
        err = p.stderr.read().decode("utf-8", "ignore") if p.stderr else ""
        p.wait()

    if not out.exists() or out.stat().st_size < 10240:
        print("[X] 录制失败:", err[-500:])
        return 1
    print("[4] 已保存: %s（%.1f KB，%.1fs）" % (out, out.stat().st_size / 1024, time.time() - t0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
