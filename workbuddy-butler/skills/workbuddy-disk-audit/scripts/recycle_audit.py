# -*- coding: utf-8 -*-
"""Windows 回收站取证：看清哪些删除项占着空间，按路径特征精确永久删除。

用户以为"删了就该空出来"，实际上文件只是进了回收站，空间照占。
本脚本解析 C:\\$Recycle.Bin\\<SID>\\$I* 元数据（格式：offset 24 是字符数，
28 起是 UTF-16LE 原始路径）还原被删文件的来路。

用法:
    python recycle_audit.py                          # 总览 + WorkBuddy 相关
    python recycle_audit.py --match clover-hub       # 只看匹配的子串
    python recycle_audit.py --match .cleanup --top 30
    python recycle_audit.py --purge --match .cleanup # 永久删除匹配项
"""
import os
import sys
import struct
import datetime

BIN_ROOT = "C:\\$Recycle.Bin"
# FOF_ALLOWUNDO 不加 = 永久删除
FO_DELETE = 3
FOF_SILENT, FOF_NOCONFIRMATION, FOF_NOERRORUI, FOF_NOCONFIRMMKDIR = 0x0004, 0x0010, 0x0400, 0x0200


def fmt(n):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}PB"


def parse_meta(i_path):
    """返回 (原始路径, 大小字节, 删除时间)。"""
    with open(i_path, "rb") as f:
        raw = f.read()
    if len(raw) < 28:
        return None, 0, None
    ver = struct.unpack_from("<Q", raw, 0)[0]
    size = struct.unpack_from("<Q", raw, 8)[0]
    ft = struct.unpack_from("<Q", raw, 16)[0]
    try:
        ts = datetime.datetime.fromtimestamp((ft - 116444736000000000) / 1e7)
    except (ValueError, OSError, OverflowError):
        ts = None
    n = struct.unpack_from("<I", raw, 24)[0]
    if ver in (1, 2):
        seg = raw[28:28 + n * 2]
    else:
        seg = raw[24:]
    path = seg.decode("utf-16-le", "ignore").rstrip("\x00")
    return path, size, ts


def collect():
    items = []
    if not os.path.isdir(BIN_ROOT):
        return items
    for sid in os.listdir(BIN_ROOT):
        b = os.path.join(BIN_ROOT, sid)
        try:
            names = os.listdir(b)
        except OSError:
            continue
        for name in names:
            if not name.startswith("$I"):
                continue
            try:
                orig, size, ts = parse_meta(os.path.join(b, name))
            except Exception:
                continue
            if not orig:
                continue
            items.append({
                "orig": orig,
                "size": size,
                "time": ts,
                "r": os.path.join(b, "$R" + name[2:]),
                "i": os.path.join(b, name),
            })
    return items


def sh_delete(path):
    import ctypes
    from ctypes import wintypes

    class OP(ctypes.Structure):
        _fields_ = [("hwnd", wintypes.HWND), ("wFunc", wintypes.UINT),
                    ("pFrom", wintypes.LPCWSTR), ("pTo", wintypes.LPCWSTR),
                    ("fFlags", ctypes.c_uint16), ("fAborted", wintypes.BOOL),
                    ("hMap", ctypes.c_void_p), ("title", wintypes.LPCWSTR)]

    op = OP()
    op.hwnd = None
    op.wFunc = FO_DELETE
    op.pFrom = os.path.abspath(path) + "\0\0"
    op.pTo = None
    op.fFlags = FOF_SILENT | FOF_NOCONFIRMATION | FOF_NOERRORUI | FOF_NOCONFIRMMKDIR
    ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
    return not os.path.exists(path)


def main():
    args = sys.argv[1:]
    match = None
    purge = "--purge" in args
    top = 15
    if "--match" in args:
        match = args[args.index("--match") + 1].lower()
    if "--top" in args:
        top = int(args[args.index("--top") + 1])

    items = collect()
    total = sum(x["size"] for x in items)
    print(f"回收站共 {len(items)} 项，{fmt(total)}")

    wb = [x for x in items if "workbuddy" in x["orig"].lower()]
    print(f"其中 WorkBuddy 相关 {len(wb)} 项，{fmt(sum(x['size'] for x in wb))}")

    sel = [x for x in items if match and match in x["orig"].lower()] if match else wb
    sel.sort(key=lambda x: -x["size"])
    print(f"\n匹配 '{match or 'workbuddy'}' 的 {len(sel)} 项，{fmt(sum(x['size'] for x in sel))}：")
    for x in sel[:top]:
        t = x["time"].strftime("%Y-%m-%d %H:%M") if x["time"] else "-"
        print(f"  {fmt(x['size']):>9}  {t}  {x['orig']}")

    if not purge:
        print("\n加 --purge 执行永久删除（不落回收站，不可恢复）")
        return

    freed = 0
    for x in sel:
        if sh_delete(x["r"]):
            sh_delete(x["i"])
            freed += x["size"]
            print(f"  已删 {fmt(x['size']):>9}  {x['orig']}")
        else:
            print(f"  失败（可能被占用）  {x['orig']}")
    print(f"\n永久删除合计 {fmt(freed)}")


if __name__ == "__main__":
    main()
