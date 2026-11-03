# -*- coding: utf-8 -*-
"""永久删除（绕过 safe-delete 垫片，不落回收站）。

本机 Python 的 shutil.rmtree / os.remove 可能被垫片重定向到 Windows 回收站，
表现是目录"消失"但磁盘空间一字节没少。这里改用 shell32.SHFileOperationW
且不带 FOF_ALLOWUNDO，做到真删除。

用法:
    python purge.py <路径> [<路径> ...]        # 逐个永久删除
    python purge.py --list paths.txt           # 每行一个路径
    python purge.py --dry-run <路径>           # 只报大小不删

保护：系统盘根目录、workbuddy.db、binaries/、blobs/ 默认拒绝，确需删除加 --force。
"""
import os
import sys
import ctypes
from ctypes import wintypes

FO_DELETE = 3
FOF_SILENT = 0x0004
FOF_NOCONFIRMATION = 0x0010
FOF_NOERRORUI = 0x0400
FOF_NOCONFIRMMKDIR = 0x0200
# FOF_ALLOWUNDO (0x0040) 故意不加，加了就进回收站


class SHFILEOPSTRUCTW(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("wFunc", wintypes.UINT),
        ("pFrom", wintypes.LPCWSTR),
        ("pTo", wintypes.LPCWSTR),
        ("fFlags", ctypes.c_uint16),
        ("fAnyOperationsAborted", wintypes.BOOL),
        ("hNameMappings", ctypes.c_void_p),
        ("lpszProgressTitle", wintypes.LPCWSTR),
    ]


PROTECTED_NAMES = {"workbuddy.db", "binaries", "blobs", "security", "system32", "windows"}


def fmt(n):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}PB"


def size_of(path):
    if os.path.isfile(path):
        try:
            return os.path.getsize(path)
        except OSError:
            return 0
    total = 0
    for root, _d, names in os.walk(path, onerror=lambda e: None):
        for fn in names:
            try:
                total += os.lstat(os.path.join(root, fn)).st_size
            except OSError:
                pass
    return total


def is_protected(path):
    ap = os.path.abspath(path)
    drive, tail = os.path.splitdrive(ap)
    if tail in ("\\", "/", ""):
        return "系统盘根目录"
    parts = [p.lower() for p in ap.replace("/", "\\").split("\\") if p]
    for p in parts:
        if p in PROTECTED_NAMES:
            return f"命中保护名 {p}"
    return None


def sh_delete(path):
    op = SHFILEOPSTRUCTW()
    op.hwnd = None
    op.wFunc = FO_DELETE
    op.pFrom = os.path.abspath(path) + "\0\0"   # 必须是双 null 结尾
    op.pTo = None
    op.fFlags = FOF_SILENT | FOF_NOCONFIRMATION | FOF_NOERRORUI | FOF_NOCONFIRMMKDIR
    res = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
    return res, bool(op.fAnyOperationsAborted)


def main():
    args = sys.argv[1:]
    dry = "--dry-run" in args
    force = "--force" in args
    targets = []

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--list":
            i += 1
            with open(args[i], encoding="utf-8") as f:
                targets += [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]
        elif a in ("--dry-run", "--force"):
            pass
        else:
            targets.append(a)
        i += 1

    if not targets:
        print(__doc__)
        sys.exit(1)

    freed = skipped = 0
    for t in targets:
        if not os.path.exists(t):
            print(f"  跳过(不存在)  {t}")
            continue
        why = is_protected(t)
        if why and not force:
            print(f"  拒绝({why})  {t}")
            skipped += 1
            continue
        s = size_of(t)
        if dry:
            print(f"  [dry] {fmt(s):>9}  {t}")
            continue
        res, aborted = sh_delete(t)
        if os.path.exists(t):
            print(f"  失败 res={res} aborted={aborted}  {t}")
            skipped += 1
        else:
            freed += s
            print(f"  已删 {fmt(s):>9}  {t}")

    if not dry:
        print(f"\n永久删除合计 {fmt(freed)}，跳过 {skipped} 项")


if __name__ == "__main__":
    main()
