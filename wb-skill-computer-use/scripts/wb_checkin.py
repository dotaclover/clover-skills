"""
方案B：无感窗体消息操作（以WorkBuddy领取每日积分为例）。

零第三方依赖，只用Python标准库ctypes。
不移动真实鼠标、不抢焦点、不受其它窗口遮挡影响。

用法：
    python wb_checkin.py probe                    # 探窗口、DPI、坐标基准
    python wb_checkin.py probe --shot cur.png     # 顺便保存窗口截图
    python wb_checkin.py status                   # 读按钮亮度，不点击
    python wb_checkin.py run                      # 安全停止，不根据亮度自动点击
    python wb_checkin.py click --center 405,1650   # 人工核对当前截图后投递点击

    # 换其它窗口/按钮
    python wb_checkin.py status --title "某客户端" --btn 100,200,150,40
    python wb_checkin.py run --title "某客户端" \
        --btn 100,200,150,40 --center 175,220 --page 80,300
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
MK_LBUTTON = 0x0001

# WorkBuddy 每日积分默认坐标（3072x1920 @200% DPI，客户区原点 0,0）
DEFAULT_TITLE = "WorkBuddy"
DEFAULT_BTN = (330, 1630, 150, 40)   # 按钮区域，采样亮度
DEFAULT_CENTER = (405, 1650)         # 按钮中心，投递点击
DEFAULT_PAGE = (60, 1680)            # 第一页分页点
GRAY_THRESHOLD = 200                 # >200 视为灰色禁用态
BLACK_THRESHOLD = 30                 # <30 视为异常


def parse_xy(value):
    parts = [int(v.strip()) for v in value.split(",")]
    if len(parts) != 2:
        raise argparse.ArgumentTypeError(f"需要 x,y 两个数字，收到 {value}")
    return tuple(parts)


def parse_box(value):
    parts = [int(v.strip()) for v in value.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError(f"需要 x,y,w,h 四个数字，收到 {value}")
    return tuple(parts)


def find_window(title=DEFAULT_TITLE):
    return user32.FindWindowW(None, title)


def window_rect(hwnd):
    r = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return r.left, r.top, r.right, r.bottom


def client_origin(hwnd):
    p = wintypes.POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(p))
    return p.x, p.y


def make_lparam(x, y):
    return (int(y) << 16) | (int(x) & 0xFFFF)


def post_click(hwnd, x, y, ox=0, oy=0):
    cx, cy = int(x) - ox, int(y) - oy
    user32.PostMessageW(hwnd, WM_MOUSEMOVE, 0, make_lparam(cx, cy))
    time.sleep(0.05)
    user32.PostMessageW(hwnd, WM_LBUTTONDOWN, MK_LBUTTON, make_lparam(cx, cy))
    time.sleep(0.08)
    user32.PostMessageW(hwnd, WM_LBUTTONUP, 0, make_lparam(cx, cy))
    time.sleep(0.4)


def window_bitmap(hwnd):
    """PrintWindow 把窗口画到内存DC，返回 (memDC, hdc, bmp, originX, originY, w, h)。"""
    l, t, r, b = window_rect(hwnd)
    w, h = r - l, b - t
    hdc = user32.GetDC(0)
    mem = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
    gdi32.SelectObject(mem, bmp)
    ok = user32.PrintWindow(hwnd, mem, 2)
    if not ok:
        gdi32.DeleteObject(bmp)
        gdi32.DeleteDC(mem)
        user32.ReleaseDC(0, hdc)
        raise RuntimeError("PrintWindow失败")
    return mem, hdc, bmp, l, t, w, h


def sample_brightness(hwnd, box, ox=0, oy=0):
    x, y, w, h = box
    mem, hdc, bmp, wx, wy, _, _ = window_bitmap(hwnd)
    total = n = 0
    try:
        for px in range(x, x + w, 4):
            for py in range(y, y + h, 4):
                c = gdi32.GetPixel(mem, px - ox - wx, py - oy - wy)
                total += ((c & 0xFF) + ((c >> 8) & 0xFF) + ((c >> 16) & 0xFF)) // 3
                n += 1
    finally:
        gdi32.DeleteObject(bmp)
        gdi32.DeleteDC(mem)
        user32.ReleaseDC(0, hdc)
    return total / n if n else 0


def save_window_png(hwnd, path, ox=0, oy=0, crop=None):
    """把 PrintWindow 结果存成PNG。纯标准库实现BGR->RGB+PNG编码。"""
    mem, hdc, bmp, wx, wy, W, H = window_bitmap(hwnd)
    if crop:
        x, y, w, h = crop
        src_x, src_y = x - ox - wx, y - oy - wy
    else:
        src_x, src_y, w, h = 0, 0, W, H

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


def get_hwnd(title):
    hwnd = find_window(title)
    if not hwnd:
        print(f"FAIL: 未找到窗口「{title}」。检查标题，或先用 gui_click.py info 列窗口。")
        sys.exit(1)
    return hwnd


def cmd_probe(args):
    print(f"物理分辨率: {user32.GetSystemMetrics(0)}x{user32.GetSystemMetrics(1)}")
    print(f"DPI缩放: {user32.GetDpiForWindow(get_hwnd(args.title)) / 96:.0%}")
    hwnd = get_hwnd(args.title)
    print(f"hwnd: {hwnd}")
    print(f"窗口矩形: {window_rect(hwnd)}")
    ox, oy = client_origin(hwnd)
    print(f"客户区原点: ({ox},{oy}) —— 屏幕坐标减这个才是客户区坐标")
    print(f"按钮区域: {args.btn}")
    print(f"按钮中心: {args.center}")
    print(f"分页点: {args.page}")
    if args.shot:
        save_window_png(hwnd, args.shot, ox, oy)


def cmd_status(args):
    hwnd = get_hwnd(args.title)
    ox, oy = client_origin(hwnd)
    value = sample_brightness(hwnd, args.btn, ox, oy)
    print(f"窗口: {args.title} hwnd={hwnd}")
    print(f"按钮区域亮度: {value:.1f}")
    print("亮度仅供参考，不能判断按钮文字或领取状态")
    return value


def cmd_run(args):
    print("已停止：不能仅凭亮度判断领取状态。请截图核对按钮文字和坐标，再使用click。")
    return 1


def cmd_click(args):
    hwnd = get_hwnd(args.title)
    ox, oy = client_origin(hwnd)
    post_click(hwnd, args.center[0], args.center[1], ox, oy)
    print("已投递一次点击，必须重新截图核实结果；投递成功不代表领取成功。")
    return 0


def main():
    p = argparse.ArgumentParser(description="无感窗体消息操作（WorkBuddy领积分示例）")
    p.add_argument("command", choices=["probe", "status", "run", "click"])
    p.add_argument("--title", default=DEFAULT_TITLE)
    p.add_argument("--btn", type=parse_box, default=DEFAULT_BTN,
                   help="按钮区域 x,y,w,h")
    p.add_argument("--center", type=parse_xy, default=DEFAULT_CENTER,
                   help="按钮中心 x,y")
    p.add_argument("--page", type=parse_xy, default=DEFAULT_PAGE,
                   help="第一页分页点 x,y；传 -1,-1 可禁用")
    p.add_argument("--gray", type=float, default=GRAY_THRESHOLD)
    p.add_argument("--black", type=float, default=BLACK_THRESHOLD)
    p.add_argument("--shot", help="probe时保存窗口截图到该路径")
    args = p.parse_args()

    if args.command == "probe":
        cmd_probe(args)
        return 0
    if args.command == "status":
        cmd_status(args)
        return 0
    if args.command == "click":
        return cmd_click(args)
    return cmd_run(args)


if __name__ == "__main__":
    sys.exit(main())
