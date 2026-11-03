# -*- coding: utf-8 -*-
"""会话数据治理：清软删除会话的磁盘残留、按保留名单裁剪工作空间记录。

背景：WorkBuddy 删除会话只是把 sessions 表里的 deleted_at 打上时间戳，
磁盘上四类文件（workspace/sessions、changes-detail、changes-index、
file-tree-manifests）和 projects/<escaped>.jsonl 一个字节都不动。

平台：Windows 为正式支持平台。macOS / Linux 下读库、备份、清残留逻辑通用，
但 projects 目录名的转义规则未实机验证（POSIX 路径按 `/x/y -> -x-y` 推断），
该部分数据可能算作 0，属已知限制而非报错。

用法:
    python session_clean.py --report
    python session_clean.py --clean-deleted --yes            # 移到 .cleanup-<ts> 并删记录
    python session_clean.py --clean-deleted --yes --purge    # 顺手永久删除
    python session_clean.py --keep "C:\\a;C:\\b" --yes       # 只留这两个空间记录
    python session_clean.py --keep "C:\\a;C:\\b" --drop-data --yes   # 连数据一起清

不加 --yes 一律只打印计划。
"""
import os
import sys
import json
import uuid
import shutil
import sqlite3
import datetime

HOME = os.path.expanduser("~")
WB = os.environ.get("WORKBUDDY_CONFIG_DIR") or os.path.join(HOME, ".workbuddy")
DB = os.path.join(WB, "workbuddy.db")
DN = os.path.join(WB, "workspace-display-names.json")
PURGE_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "purge.py")


def fmt(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}GB"


def size_of(p):
    if os.path.isfile(p):
        try:
            return os.path.getsize(p)
        except OSError:
            return 0
    total = 0
    for root, _d, names in os.walk(p, onerror=lambda e: None):
        for fn in names:
            try:
                total += os.lstat(os.path.join(root, fn)).st_size
            except OSError:
                pass
    return total


def norm(p):
    return (p or "").replace("\\", "/").lower().rstrip("/")


def escaped(cwd):
    return norm(cwd).replace(":/", "-").replace("/", "-")


def uuid_of(sid):
    h = (sid or "").replace("-", "")
    if len(h) != 32:
        return None
    try:
        return str(uuid.UUID(h))
    except ValueError:
        return None


def connect():
    con = sqlite3.connect(DB, timeout=30)
    con.execute("PRAGMA busy_timeout=30000")
    return con


def backup(tag="pre-clean"):
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    base = os.path.join(WB, ".cleanup-" + ts)
    os.makedirs(base, exist_ok=True)
    src = sqlite3.connect(DB, timeout=30)
    dst = sqlite3.connect(os.path.join(base, "workbuddy.db.bak"))
    with dst:
        src.backup(dst)
    dst.close()
    src.close()
    if os.path.isfile(DN):
        shutil.copy2(DN, os.path.join(base, "workspace-display-names.json.bak"))
    return base


class Trash:
    def __init__(self, base):
        self.dir = os.path.join(base, "trash")
        os.makedirs(self.dir, exist_ok=True)
        self.moved = []

    def move(self, path, tag):
        if not os.path.exists(path):
            return 0
        s = size_of(path)
        d = os.path.join(self.dir, tag)
        os.makedirs(d, exist_ok=True)
        name = os.path.basename(path.rstrip("\\/")) or "root"
        dst = os.path.join(d, name)
        n = 1
        while os.path.exists(dst):
            dst = os.path.join(d, f"{name}.{n}")
            n += 1
        try:
            os.rename(path, dst)
        except OSError as e:
            print(f"  移不动 {path}: {str(e)[:60]}")
            return 0
        self.moved.append({"src": path, "dst": dst, "size": s})
        return s


def report():
    con = connect()
    rows = con.execute("SELECT id, cwd, title, deleted_at FROM sessions").fetchall()
    ws = [r[0] for r in con.execute("SELECT path FROM workspaces")]
    con.close()

    alive = {uuid_of(s) for s, _c, _t, d in rows if not d}
    dead = {uuid_of(s) for s, _c, _t, d in rows if d} - alive
    print(f"会话 {len(rows)} 条：存活 {len(alive)}，软删除 {len(dead)}")
    print(f"workspaces 表 {len(ws)} 条：" + "、".join(ws or ["<空>"]))

    dead_bytes = 0
    for u in dead:
        if not u:
            continue
        for p in (os.path.join(WB, "workspace", "sessions", u),
                  os.path.join(WB, "changes-detail", u),
                  os.path.join(WB, "changes-index", u),
                  os.path.join(WB, "file-tree-manifests", u + ".json")):
            dead_bytes += size_of(p)

    proots = os.path.join(WB, "projects")
    dead_jsonl = 0
    if os.path.isdir(proots):
        for root, _d, names in os.walk(proots):
            for fn in names:
                if fn.endswith(".jsonl") and fn[:-6] not in alive:
                    try:
                        dead_jsonl += os.path.getsize(os.path.join(root, fn))
                    except OSError:
                        pass
    print(f"软删除会话的 diff 索引残留：{fmt(dead_bytes)}")
    print(f"无主/已删会话的正文 jsonl：{fmt(dead_jsonl)}")
    print(f"可回收合计：{fmt(dead_bytes + dead_jsonl)}")


def clean_deleted(trash, do_purge):
    con = connect()
    rows = con.execute("SELECT id, deleted_at FROM sessions").fetchall()
    alive = {uuid_of(s) for s, d in rows if not d}
    dead = {uuid_of(s) for s, d in rows if d} - alive

    total = 0
    for u in dead:
        if not u:
            continue
        for p in (os.path.join(WB, "workspace", "sessions", u),
                  os.path.join(WB, "changes-detail", u),
                  os.path.join(WB, "changes-index", u),
                  os.path.join(WB, "file-tree-manifests", u + ".json")):
            total += trash.move(p, "dead-session")

    proots = os.path.join(WB, "projects")
    if os.path.isdir(proots):
        for root, _d, names in os.walk(proots):
            for fn in names:
                if not fn.endswith(".jsonl") or fn[:-6] in alive:
                    continue
                total += trash.move(os.path.join(root, fn), "dead-jsonl")

    n = con.execute("DELETE FROM sessions WHERE deleted_at IS NOT NULL").rowcount
    con.commit()
    con.close()
    print(f"  清理 {fmt(total)}，移除已删会话记录 {n} 条")
    if do_purge:
        os.system(f'python "{PURGE_SCRIPT}" --force "{trash.dir}"')
    return total


def prune_workspaces(trash, keep, drop_data):
    keep_norm = {norm(k) for k in keep}
    con = connect()
    rows = con.execute("SELECT id, cwd FROM sessions").fetchall()
    removed_ws = []
    for (p,) in con.execute("SELECT path FROM workspaces").fetchall():
        if norm(p) not in keep_norm:
            con.execute("DELETE FROM workspaces WHERE path=?", (p,))
            removed_ws.append(p)

    dropped = 0
    if drop_data:
        for sid, cwd in rows:
            if norm(cwd) in keep_norm:
                continue
            u = uuid_of(sid)
            if u:
                for sub in ("workspace/sessions", "changes-detail", "changes-index"):
                    dropped += trash.move(os.path.join(WB, *sub.split("/"), u), "drop-ws")
                dropped += trash.move(os.path.join(WB, "file-tree-manifests", u + ".json"), "drop-ws")
            con.execute("DELETE FROM sessions WHERE id=?", (sid,))
        for cwd_norm in {norm(c) for _s, c in rows} - keep_norm:
            # 正文目录按 cwd 归属
            esc = None
            for _s, c in rows:
                if norm(c) == cwd_norm and c:
                    esc = escaped(c)
                    break
            if esc:
                dropped += trash.move(os.path.join(WB, "projects", esc), "drop-ws")
    con.commit()
    con.close()

    if os.path.isfile(DN):
        dn = json.load(open(DN, encoding="utf-8"))
        before = len(dn.get("workspaces", {}))
        dn["workspaces"] = {k: v for k, v in dn.get("workspaces", {}).items()
                            if norm(v.get("path")) in keep_norm}
        json.dump(dn, open(DN, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"  移除空间记录 {removed_ws}，显示名 {before} -> {len(dn['workspaces'])}")
        print("  保留：" + "、".join(v.get("displayName", "?") for v in dn["workspaces"].values()))
    if drop_data:
        print(f"  连带清理数据 {fmt(dropped)}")
    return dropped


def main():
    args = sys.argv[1:]
    yes = "--yes" in args
    do_purge = "--purge" in args
    drop_data = "--drop-data" in args
    keep = []
    if "--keep" in args:
        keep = [x for x in args[args.index("--keep") + 1].split(";") if x.strip()]

    if os.name != "nt":
        print("⚠️  非 Windows 平台：读库与清理逻辑通用，但 projects 转义目录未验证，可能算作 0。\n")

    if "--report" in args or (not keep and "--clean-deleted" not in args):
        report()
        return

    if not yes:
        print("[计划] 以下操作需要加 --yes 才执行")
        if "--clean-deleted" in args:
            print("  - 清软删除会话的磁盘残留，并删除 sessions 表里的已删行")
        if keep:
            print(f"  - 工作空间记录只保留 {keep}" + ("，并删除其余空间的数据" if drop_data else ""))
        return

    base = backup()
    print(f"备份：{base}")
    trash = Trash(base)
    if "--clean-deleted" in args:
        print("== 清理软删除会话 ==")
        clean_deleted(trash, do_purge)
    if keep:
        print("== 裁剪工作空间 ==")
        prune_workspaces(trash, keep, drop_data)

    if trash.moved:
        with open(os.path.join(base, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump({"moved": trash.moved}, f, ensure_ascii=False, indent=1)
        print(f"\n移入 {base}/trash，共 {fmt(sum(m['size'] for m in trash.moved))}")
        if not do_purge:
            print(f"确认无误后永久删除：python purge.py --force \"{trash.dir}\"")


if __name__ == "__main__":
    main()
