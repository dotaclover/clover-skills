# -*- coding: utf-8 -*-
"""回收站取证：看清哪些删除项占着空间，按路径特征精确永久删除。

用户以为"删了就该空出来"，实际上文件只是进了回收站，空间照占。

平台：Windows 为正式支持平台，解析 C:\\$Recycle.Bin\\<SID>\\$I* 元数据
（offset 24 是字符数，28 起是 UTF-16LE 原始路径）还原被删文件的来路。
macOS（~/.Trash）与 Linux（Trash/info/*.trashinfo）只做基础列举：mac 拿不到原始
完整路径，只有文件名与 mtime；Linux 能读到 Path= 但未实机验证。两者均不保证准确。

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

IS_WIN = os.name == "nt"
IS_MAC = sys.platform == "darwin"
HOME = os.path.expanduser("~")

if IS_WIN:
    BIN_ROOT = "C:\\$Recycle.Bin"
elif IS_MAC:
    BIN_ROOT = os.path.join(HOME, ".Trash")
else:
    BIN_ROOT = os.path.join(HOME, ".local", "share", "Trash", "files")
TRASH_INFO = os.path.join(HOME, ".local", "share", "Trash", "info")

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


def dir_size(p):
    total = 0
    for root, _d, names in os.walk(p, onerror=lambda e: None):
        for fn in names:
            try:
                total += os.lstat(os.path.join(root, fn)).st_size
            except OSError:
                pass
    return total


def collect_posix():
    """macOS ~/.Trash 与 Linux Trash/files 的基础列举。准确性不保证。"""
    items = []
    try:
        names = os.listdir(BIN_ROOT)
    except OSError:
        return items
    for name in names:
        p = os.path.join(BIN_ROOT, name)
        try:
            st = os.lstat(p)
        except OSError:
            continue
        orig = name                      # macOS 只能拿到文件名，拿不到原路径
        ts = datetime.datetime.fromtimestamp(st.st_mtime)
        if not IS_MAC:                   # Linux 的 .trashinfo 里有 Path= 与 DeletionDate=
            info = os.path.join(TRASH_INFO, name + ".trashinfo")
            if os.path.isfile(info):
                try:
                    with open(info, encoding="utf-8", errors="ignore") as f:
                        for ln in f:
                            if ln.startswith("Path="):
                                orig = ln[5:].strip()
                            elif ln.startswith("DeletionDate="):
                                try:
                                    ts = datetime.datetime.strptime(
                                        ln[14:].strip(), "%Y-%m-%dT%H:%M:%S")
                                except ValueError:
                                    pass
                except OSError:
                    pass
        size = dir_size(p) if os.path.isdir(p) and not os.path.islink(p) else st.st_size
        items.append({"orig": orig, "size": size, "time": ts, "r": p, "i": None})
    return items


def collect():
    items = []
    if not os.path.isdir(BIN_ROOT):
        return items
    if not IS_WIN:
        return collect_posix()
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


def delete_any(path):
    """Windows 走 SHFileOperationW 真删除；其他平台走 shutil 基础实现（未实机验证）。"""
    if not path or not os.path.exists(path):
        return True
    if IS_WIN:
        return sh_delete(path)
    import shutil
    try:
        if os.path.isdir(path) and not os.path.islink(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
        return True
    except OSError as e:
        print(f"    ({type(e).__name__}: {e})")
        return False


def main():
    args = sys.argv[1:]
    match = None
    purge = "--purge" in args
    top = 15
    if "--match" in args:
        match = args[args.index("--match") + 1].lower()
    if "--top" in args:
        top = int(args[args.index("--top") + 1])

    if not IS_WIN:
        print("⚠️  非 Windows 平台：回收站解析为基础实现，macOS 拿不到完整原路径，结果仅作参考。\n")

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
        if delete_any(x["r"]):
            if x["i"]:
                delete_any(x["i"])
            freed += x["size"]
            print(f"  已删 {fmt(x['size']):>9}  {x['orig']}")
        else:
            print(f"  失败（可能被占用）  {x['orig']}")
    print(f"\n永久删除合计 {fmt(freed)}")


if __name__ == "__main__":
    main()
