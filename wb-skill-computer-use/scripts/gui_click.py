"""
方案A配套裸脚本：真实鼠标点击（会移动光标、抢焦点）。

只适合用户不在电脑前时用。要无感操作请用 wb_checkin.py。
零第三方依赖，只用标准库ctypes。

用法：
    python gui_click.py info
    python gui_click.py shot --out cur.png
    python gui_click.py shot --out crop.png --region 0,1440,560,360
    python gui_click.py click 405 1650
    python gui_click.py scroll -120 500 800
"""
import argparse
import ctypes
import struct
import sys
import time
import zlib
from ctypes import wintypes

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
user32.SetProcessDPIAware()

WM_MOUSEMOVE = 0x0200
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205
WM_MOUSEWHEEL = 0x0800


def parse_xy(value):
    parts = [int(v.strip()) for v in value.split(",")]
    if len(parts) != 2:
        raise argparse.ArgumentTypeError(f"需要 x,y，收到 {value}")
    return tuple(parts)


def parse_box(value):
    parts = [int(v.strip()) for v in value.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError(f"需要 x,y,w,h，收到 {value}")
    return tuple(parts)


def list_windows():
    results = []
    cb_type = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

    def callback(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        buf = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, buf, 512)
        if buf.value:
            r = wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(r))
            results.append((hwnd, buf.value, (r.left, r.top, r.right, r.bottom)))
        return True

    user32.EnumWindows(cb_type(callback), 0)
    return results


def move(x, y):
    user32.SetCursorPos(int(x), int(y))
    time.sleep(0.1)


def click(x, y, button="left"):
    move(x, y)
    if button == "left":
        down, up = WM_LBUTTONDOWN, WM_LBUTTONUP
    else:
        down, up = WM_RBUTTONDOWN, WM_RBUTTONUP
    user32.mouse_event(down, 0, 0, 0, 0)
    time.sleep(0.08)
    user32.mouse_event(up, 0, 0, 0, 0)


def scroll(amount, x, y):
    move(x, y)
    user32.mouse_event(WM_MOUSEWHEEL, 0, 0, int(amount), 0)


def save_png(path, x, y, w, h):
    hdc = user32.GetDC(0)
    mem = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
    gdi32.SelectObject(mem, bmp)
    gdi32.BitBlt(mem, 0, 0, w, h, hdc, x, y, 0x00CC0020)

    class BMI(ctypes.Structure):
        _fields_ = [
            ("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
            ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
            ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
            ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
            ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
            ("biClrImportant", wintypes.DWORD),
        ]

    bi = BMI()
    bi.biSize = ctypes.sizeof(bi)
    bi.biWidth = w
    bi.biHeight = -h
    bi.biPlanes = 1
    bi.biBitCount = 24
    bi.biCompression = 0
    stride = ((w * 3 + 3) // 4) * 4
    buf = ctypes.create_string_buffer(stride * h)
    gdi32.GetDIBits(mem, bmp, 0, h, buf, ctypes.byref(bi), 0)

    rows = []
    for row in range(h):
        line = buf.raw[row * stride:row * stride + w * 3]
        rgb = bytearray()
        for i in range(0, len(line), 3):
            rgb += bytes((line[i + 2], line[i + 1], line[i]))
        rows.append(b"\x00" + bytes(rgb))
    raw = b"".join(rows)

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 6))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)

    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(mem)
    user32.ReleaseDC(0, hdc)
    print(f"截图已保存: {path} ({w}x{h})")


def main():
    p = argparse.ArgumentParser(description="真实鼠标点击（会干扰用户，谨慎使用）")
    p.add_argument("command", choices=["info", "shot", "click", "scroll"])
    p.add_argument("pos", nargs="?", type=parse_xy)
    p.add_argument("--out", default="screen.png")
    p.add_argument("--region", type=parse_box)
    p.add_argument("--button", choices=["left", "right"], default="left")
    args = p.parse_args()

    if args.command == "info":
        print(f"屏幕: {user32.GetSystemMetrics(0)}x{user32.GetSystemMetrics(1)}")
        for hwnd, title, rect in list_windows():
            print(f"{hwnd:>10}  {title[:50]:<52} {rect}")
    elif args.command == "shot":
        if args.region:
            x, y, w, h = args.region
        else:
            x = y = 0
            w, h = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
        save_png(args.out, x, y, w, h)
    elif args.command == "click":
        if not args.pos:
            p.error("click 需要 x,y")
        click(args.pos[0], args.pos[1], args.button)
        print(f"已点击 {args.pos} ({args.button})")
    elif args.command == "scroll":
        if not args.pos:
            p.error("scroll 需要 x,y")
        amount = int(args.pos[0])
        scroll(amount, args.pos[1], args.pos[2])
        print(f"已在 {args.pos[1:]} 滚动 {amount}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
