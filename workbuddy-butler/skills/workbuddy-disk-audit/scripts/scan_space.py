# -*- coding: utf-8 -*-
"""WorkBuddy 空间台账：把各处占用按「可删性」分类打出来。

用法:
    python scan_space.py            # 人读表格
    python scan_space.py --json     # 机器读，便于后续脚本消费
"""
import os
import sys
import json
import sqlite3
import struct
import shutil

HOME = os.path.expanduser("~")
WB = os.environ.get("WORKBUDDY_CONFIG_DIR") or os.path.join(HOME, ".workbuddy")
ROAM = os.path.join(os.environ.get("APPDATA", ""), "WorkBuddy")
INSTALL = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "WorkBuddy")
LEGACY = os.path.join(HOME, "WorkBuddy")

# 顶层目录 -> (档位, 说明)
GRADE = {
    "binaries": ("D", "Node/Python/Git 运行时，删了技能全废"),
    "blobs": ("D", "聊天附件与图片，删了旧会话图片裂"),
    "security": ("D", "安全威胁库"),
    "external-packages": ("D", "外部依赖包"),
    "appearance-resources": ("D", "界面资源"),
    "native-runtimes": ("D", "原生运行时"),
    "plugins": ("C", "插件本体与缓存，运行中清 cache 会坏插件"),
    "projects": ("B", "会话正文 jsonl，按工作空间归属"),
    "workspace": ("B", "会话工作文件，主体是 modify_backup 回滚备份"),
    "changes-detail": ("B", "改动 diff 详情"),
    "file-tree-manifests": ("B", "文件树快照"),
    "changes-index": ("B", "改动索引"),
    "sessions": ("B", "会话索引"),
    "logs": ("A", "运行日志，当天文件被占用"),
    "cache": ("A", "产品缓存，可重建"),
    "clipboard-images": ("A", "剪贴板截图"),
    "file-history": ("A", "文件撤销历史，删了旧编辑不能退回"),
    "app": ("A", "Electron 缓存为主，分区里的登录态要留"),
    "connectors-marketplace": ("B", "连接器市场仓库，重下可恢复"),
    "skills-marketplace": ("B", "技能市场仓库，重下可恢复"),
    "skills": ("D", "已安装技能"),
    "storage": ("D", "账户存储"),
    "local_storage": ("D", "应用本地状态"),
    "browser-runtime": ("D", "浏览器运行时"),
    "audit-log": ("A", "审计日志，删了丢历史操作记录"),
    "traces": ("A", "调用链追踪，可删"),
    "shell-snapshots": ("A", "shell 快照，可删"),
    "pending-telemetry": ("A", "待上报遥测"),
    "assistant-display": ("D", "会话展示缓存，删了列表可能重建"),
    "artifact-index": ("B", "产物索引，删了产物面板需重建"),
    "tasks": ("D", "任务列表"),
    "memory": ("D", "记忆文件，删了丢长期上下文"),
    "brain": ("D", "记忆索引"),
    "logs_old": ("A", "过期日志"),
}

# 前缀规则：命中即用
PREFIX_GRADE = [
    (".cleanup-", ("A", "本工具自己的回收目录，可整包删")),
]


def dir_size(path):
    if os.path.isfile(path):
        try:
            return os.path.getsize(path), 1
        except OSError:
            return 0, 0
    total = files = 0
    for root, _dirs, names in os.walk(path, onerror=lambda e: None):
        for fn in names:
            try:
                total += os.lstat(os.path.join(root, fn)).st_size
                files += 1
            except OSError:
                pass
    return total, files


def fmt(n):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}PB"


def uuid_of(sid):
    h = (sid or "").replace("-", "")
    if len(h) != 32:
        return None
    try:
        import uuid
        return str(uuid.UUID(h))
    except ValueError:
        return None


def norm(p):
    return (p or "").replace("\\", "/").lower().rstrip("/")


def escaped(cwd):
    """工作空间路径 -> projects 下的目录名。C:/x 必须把 ':/' 整体换成一个 '-'。"""
    return norm(cwd).replace(":/", "-").replace("/", "-")


def scan_workspaces():
    """按 cwd 归组，算出每个工作空间的会话数据占用。"""
    db = os.path.join(WB, "workbuddy.db")
    if not os.path.isfile(db):
        return []
    try:
        con = sqlite3.connect("file:" + db + "?mode=ro", uri=True, timeout=5)
        rows = con.execute("SELECT id, cwd, title, deleted_at FROM sessions").fetchall()
        con.close()
    except sqlite3.Error:
        return []

    groups = {}
    for sid, cwd, title, deleted_at in rows:
        key = norm(cwd) or "<未记录>"
        g = groups.setdefault(key, {"cwd": cwd or "", "alive": 0, "deleted": 0,
                                    "session_files": 0, "jsonl": 0, "dead_bytes": 0})
        g["deleted" if deleted_at else "alive"] += 1
        u = uuid_of(sid)
        if not u:
            continue
        sub = 0
        for p in (os.path.join(WB, "workspace", "sessions", u),
                  os.path.join(WB, "changes-detail", u),
                  os.path.join(WB, "changes-index", u),
                  os.path.join(WB, "file-tree-manifests", u + ".json")):
            s, _ = dir_size(p)
            sub += s
        g["session_files"] += sub
        if deleted_at:
            g["dead_bytes"] += sub

    # 正文 jsonl 按文件名归属
    proots = os.path.join(WB, "projects")
    if os.path.isdir(proots):
        for cwd_key, g in groups.items():
            if not g["cwd"]:
                continue          # cwd 缺失的会话归不到任何 projects 目录
            p = os.path.join(proots, escaped(g["cwd"]))
            if os.path.isdir(p):
                s, _ = dir_size(p)
                g["jsonl"] = s

    out = []
    for key, g in groups.items():
        out.append({
            "cwd": g["cwd"],
            "alive": g["alive"],
            "deleted": g["deleted"],
            "session_files": g["session_files"],
            "jsonl": g["jsonl"],
            "dead_bytes": g["dead_bytes"],
            "total": g["session_files"] + g["jsonl"],
        })
    out.sort(key=lambda x: -x["total"])
    return out


def scan_recycle():
    """Windows 回收站里与 WorkBuddy 相关的条目。"""
    root = "C:\\$Recycle.Bin"
    total = wb_bytes = wb_items = 0
    if not os.path.isdir(root):
        return {"total": 0, "workbuddy": 0, "items": 0}
    for sid_dir in os.listdir(root):
        b = os.path.join(root, sid_dir)
        try:
            names = os.listdir(b)
        except OSError:
            continue
        for name in names:
            if not name.startswith("$I"):
                continue
            try:
                raw = open(os.path.join(b, name), "rb").read()
                if len(raw) < 28:
                    continue
                ver = struct.unpack_from("<Q", raw, 0)[0]
                size = struct.unpack_from("<Q", raw, 8)[0]
                n = struct.unpack_from("<I", raw, 24)[0]
                seg = raw[28:28 + n * 2] if ver in (1, 2) else raw[24:]
                orig = seg.decode("utf-16-le", "ignore").rstrip("\x00")
            except Exception:
                continue
            total += size
            if "workbuddy" in orig.lower():
                wb_bytes += size
                wb_items += 1
    return {"total": total, "workbuddy": wb_bytes, "items": wb_items}


def main():
    want_json = "--json" in sys.argv
    report = {"paths": {}, "top": [], "workspaces": [], "recycle": {}, "disk": {}}

    for label, p in ((".workbuddy", WB), ("Roaming", ROAM),
                     ("Install", INSTALL), ("LegacyUserDir", LEGACY)):
        s, c = dir_size(p) if os.path.isdir(p) else (0, 0)
        report["paths"][label] = {"path": p, "size": s, "files": c,
                                  "exists": os.path.isdir(p)}

    if os.path.isdir(WB):
        for name in os.listdir(WB):
            p = os.path.join(WB, name)
            if not os.path.isdir(p):
                continue
            s, c = dir_size(p)
            grade, note = GRADE.get(name, ("?", "未分类"))
            for prefix, val in PREFIX_GRADE:
                if name.startswith(prefix):
                    grade, note = val
                    break
            else:
                # 32 位 hex 的目录是按用户分的存储
                if len(name) >= 32 and name.replace("-", "")[:32].isalnum():
                    grade, note = "D", "用户级存储"
            report["top"].append({"name": name, "size": s, "files": c,
                                  "grade": grade, "note": note})
        report["top"].sort(key=lambda x: -x["size"])

    report["workspaces"] = scan_workspaces()
    report["recycle"] = scan_recycle()
    try:
        t, u, f = shutil.disk_usage(os.path.splitdrive(WB)[0] + "\\")
        report["disk"] = {"total": t, "used": u, "free": f}
    except OSError:
        pass

    if want_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    print("=== 各位置占用 ===")
    for label, info in report["paths"].items():
        state = "" if info["exists"] else "  (不存在)"
        print(f"  {fmt(info['size']):>9} {info['files']:>6}文件  {label:<14}{info['path']}{state}")
    if report["disk"]:
        d = report["disk"]
        print(f"\n  磁盘可用 {fmt(d['free'])} / 总 {fmt(d['total'])}")

    print("\n=== .workbuddy 一级目录 ===")
    print(f"  {'大小':>9}  {'档位':<4} 目录")
    for it in report["top"]:
        print(f"  {fmt(it['size']):>9}  {it['grade']:<4} {it['name']}/  — {it['note']}")

    print("\n=== 按工作空间 ===")
    print(f"  {'合计':>9}  {'会话(活/删)':>12}  {'会话文件':>9} {'正文':>9}  路径")
    for w in report["workspaces"]:
        print(f"  {fmt(w['total']):>9}  {w['alive']:>4}/{w['deleted']:<7}  "
              f"{fmt(w['session_files']):>9} {fmt(w['jsonl']):>9}  {w['cwd'] or '<未记录>'}")

    r = report["recycle"]
    print(f"\n=== 回收站 ===  总计 {fmt(r['total'])}，其中 WorkBuddy 相关 {fmt(r['workbuddy'])} / {r['items']} 项")
    if r["workbuddy"] > 0:
        print("  这些条目仍占磁盘，用 recycle_audit.py 处理。")

    print("\n档位：A 可直接删 / B 需用户确认 / C 慎动 / D 禁动")


if __name__ == "__main__":
    main()
