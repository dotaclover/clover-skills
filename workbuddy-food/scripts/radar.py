#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
workbuddy-food 本地数据管理：候选池 -> 硬核验判定 -> 全天决策表
v1.2：营业已确认(open)排前；未验活(unknown)不再出局，进表标注后排后。

设计边界：
  本脚本【不操作浏览器】，只负责把已采集到的数据落库、判定、排序、出表。
  浏览器取数由 WorkBuddy 的浏览器 MCP 完成（见 SKILL.md §能力边界）。

零第三方依赖，仅标准库。Python 3.8+。

常用：
  python radar.py init --city 广州 --area 江南西 --dish 炒牛河
  python radar.py add --name 华叻强面家 --address "紫龙大街24号之9" --hours 07:00-22:30 ...
  python radar.py report
"""

import argparse
import json
import math
import os
import sys
import unicodedata
from datetime import datetime

# ---------------------------------------------------------------- 基础设施

if hasattr(sys.stdout, "reconfigure"):
    try:
        # 不强制 UTF-8：跟随环境编码，否则 Windows PowerShell 管道捕获时会乱码。
        # 只把错误处理降级，避免个别符号在 GBK 环境下抛 UnicodeEncodeError。
        sys.stdout.reconfigure(errors="replace")
        sys.stderr.reconfigure(errors="replace")
    except Exception:
        pass

DEFAULT_DB_DIR = ".food-radar"

# 时段代表时间点（分钟）
SLOTS = [
    ("早餐", 8 * 60),
    ("午市", 12 * 60 + 30),
    ("晚市", 19 * 60),
    ("宵夜", 23 * 60),
]

FIELDS = [
    "name", "branch", "address", "landmark", "avg_price", "hours",
    "rating", "review_count", "signature", "signature_note",
    "source", "data_date", "area_confirmed", "note",
    "status",           # 经营状态：open / closed / unknown，第 0 项硬核验
    "last_seen",        # 最近一次被证实营业的时点，如 2026-10
]


def die(msg):
    print("错误: " + msg, file=sys.stderr)
    sys.exit(1)


def resolve_db(path, query=None):
    """确定数据文件路径。

    - 显式 --db：直接用
    - 有 query：按 城市_商圈_品类 生成 slug（init 用）
    - 都没有：目录下若只有一个池子就用它，多个则报错要求指定
    """
    base = os.path.abspath(DEFAULT_DB_DIR)
    if path:
        return os.path.abspath(path)
    if query:
        slug = "_".join(
            x for x in [query.get("city"), query.get("area"), query.get("dish")] if x
        )
        slug = slug.replace(" ", "").replace("/", "-") or "default"
        return os.path.join(base, slug + ".json")
    if os.path.isdir(base):
        files = sorted(f for f in os.listdir(base) if f.endswith(".json"))
        if len(files) == 1:
            return os.path.join(base, files[0])
        if len(files) > 1:
            die("目录里有多份候选池，请用 --db 指定：\n  " +
                "\n  ".join(os.path.join(base, f) for f in files))
    return os.path.join(base, "default.json")


def load(db_path):
    if not os.path.exists(db_path):
        die(
            "找不到数据文件 %s\n  先执行 init 建立候选池：\n"
            "  python radar.py init --city 广州 --area 江南西 --dish 炒牛河" % db_path
        )
    with open(db_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save(data, db_path):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    with open(db_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return db_path


def find(data, name):
    """按店名模糊匹配，返回 [(index, candidate)]。"""
    key = name.strip()
    hits = []
    for i, c in enumerate(data.get("candidates", [])):
        if key == c.get("name") or key in c.get("name", ""):
            hits.append((i, c))
    return hits


# ---------------------------------------------------------------- 时段解析

def parse_hours(hours):
    """把营业时间字符串解析成若干 [start, end) 分钟区间，跨零点展开成 >1440。

    支持：07:00-22:30 / 17:00-02:00 / 11:00-14:00,17:00-21:00 / 17:00-次日02:00
    v1.2：支持「全天 / 24小时 / 通宵 / 00:00-24:00」，返回 [(0, 1440)]。
    解析失败返回 None。
    """
    if not hours:
        return None
    raw = str(hours).strip()
    if raw in ("00:00-24:00", "0:00-24:00") or any(
            m in raw for m in ("全天", "24小时", "24h", "24H", "通宵")):
        return [(0, 24 * 60)]
    for junk in ["次日", "翌日", "次日凌晨", "凌晨", "—", "~", "至", " ", "\u3000"]:
        raw = raw.replace(junk, "-" if junk in ("—", "~", "至") else "")
    segs = []
    for part in raw.replace("，", ",").replace("、", ",").split(","):
        part = part.strip()
        if not part or "-" not in part:
            continue
        try:
            a, b = part.split("-", 1)
            ah, am = [int(x) for x in a.strip().split(":")]
            bh, bm = [int(x) for x in b.strip().split(":")]
            start = ah * 60 + am
            end = bh * 60 + bm
            if end <= start:
                end += 24 * 60
            segs.append((start, end))
        except Exception:
            continue
    return segs or None


def open_at(segs, minute):
    if not segs:
        return None
    for start, end in segs:
        if start <= minute < end or start <= minute + 24 * 60 < end:
            return True
    return False


def slot_hint(hours):
    """该店能被哪些时段覆盖。v1.2：四段全覆盖叫「全天」，缺时间叫「未确认」。

    这是全天视角的覆盖表，不是「提问当下是否开门」——用户问的未必是现在。
    """
    segs = parse_hours(hours)
    if not segs:
        return "未确认"
    names = [label for label, t in SLOTS if open_at(segs, t)]
    if len(names) == len(SLOTS):
        return "全天"
    return "、".join(names) if names else "时段外"


# ---------------------------------------------------------------- 判定逻辑

def judge(c, query):
    """对单个候选跑第 0 项（经营状态）+ 四项硬核验，返回 (verdict dict)。不修改原数据。"""
    v = {}

    # 0) 经营状态：v1.2 起不再是闸门，只是排序主键。
    #    「页面/POI 还在」依然不等于「店还开着」，但 unknown 不再把店踢出表；
    #    只有确证 closed / elsewhere 才一票否决。未验活店进表、标注、排后。
    st = str(c.get("status") or "unknown").strip().lower()
    if st in ("closed", "已闭店", "停业", "歇业", "搬迁", "0", "false"):
        v["operating"] = "closed"
    elif st in ("open", "营业中", "在营", "1", "true", "yes"):
        v["operating"] = "open"
    elif st in ("异地", "elsewhere", "same_name_elsewhere"):
        v["operating"] = "elsewhere"
    else:
        v["operating"] = "unknown"

    addr = (c.get("address") or "").strip()
    landmark = (c.get("landmark") or "").strip()
    area = (query.get("area") or "").strip()
    city = (query.get("city") or "").strip()

    # 1) 地址：是否精确到门牌
    has_num = any(ch.isdigit() for ch in addr)
    if addr and has_num:
        v["address"] = "ok"
    elif addr:
        v["address"] = "partial"   # 有街道无门牌
    else:
        v["address"] = "missing"

    # 2) 商圈归属（软判定：只提示，不直接出局）
    #    有些真实地址用街道名（紫龙大街 24 号），不含商圈名，硬匹配会误杀。
    #    已人工确认归属的，用 area_confirmed=True 标记，不再提示。
    text = addr + landmark + (c.get("branch") or "")
    if c.get("area_confirmed"):
        v["area"] = "ok"
    elif area and area in text:
        v["area"] = "ok"
    elif city and city in text:
        v["area"] = "city_only"
    elif addr:
        v["area"] = "unclear"
    else:
        v["area"] = "unknown"

    # 3) 招牌菜归属：唯一可以一票否决的项
    sig = (c.get("signature") or "unknown").strip().lower()
    if sig in ("yes", "y", "1", "true"):
        v["signature"] = "ok"
    elif sig in ("no", "n", "0", "false"):
        v["signature"] = "mismatch"
    else:
        v["signature"] = "unknown"

    # 4) 人均
    v["price"] = "ok" if c.get("avg_price") not in (None, "", 0) else "missing"

    # 5) 营业时间
    segs = parse_hours(c.get("hours"))
    v["hours"] = "ok" if segs else "missing"
    v["slots"] = slot_hint(c.get("hours"))

    # 确认项计数（area 不计入，因为它不可靠地判真假）
    core = [v["address"], v["signature"], v["price"], v["hours"]]
    v["confirmed"] = sum(1 for x in core if x == "ok")
    v["total"] = 4

    # L0 出局判定：一票否决，布尔量，绝不参与打分
    gates = []
    if v["operating"] == "closed":
        gates.append(("已闭店/停业", "第 0 项经营状态：确证闭店、停业或搬迁"))
    if v["operating"] == "elsewhere":
        gates.append(("同名异地", "确证不在目标商圈"))
    if v["signature"] == "mismatch":
        gates.append(("招牌错配", "目标菜不是该店招牌"))
    if v["confirmed"] == 0:
        gates.append(("四项全无确认", "地址/招牌/人均/营业时间无一项可核"))
    v["gates"] = gates
    v["excluded"] = bool(gates)
    v["exclude_reason"] = "；".join(g[0] for g in gates)

    # 风险提示
    warns = []
    if v["operating"] == "unknown":
        warns.append("经营状态未确认：页面/POI 存在不等于店还开着，需电话或登录态地图复核")
    if v["area"] == "unclear" and addr:
        warns.append("地址未含商圈名，需人工确认所属商圈（可能是异地同名店）")
    if v["area"] == "city_only":
        warns.append("只有市级信息，缺商圈级定位")
    if v["address"] == "partial":
        warns.append("地址无门牌号，只到街道")
    if v["hours"] == "missing":
        warns.append("营业时间未确认，可能跑空")
    if v["price"] == "missing":
        warns.append("人均未确认")
    dd = str(c.get("data_date") or "")
    toks = [t.strip() for t in dd.replace("年", "-").replace("月", "-")
            .replace("/", "-").split("-") if t.strip().isdigit()]
    yr, ym = None, None
    if toks and len(toks[0]) == 4:
        yr = int(toks[0])
        ym = (yr, int(toks[1]) if len(toks) > 1 else 1)
    if yr and yr <= datetime.now().year - 2:
        warns.append("数据年份 %d，价格/时间可能已失效" % yr)

    # 时间衰减：口碑数据超过 12 个月，评分/评论数不再计入排序。
    # 老店评论数是历史累积，越多反而越可能是「关店前的存档」。
    now = datetime.now()
    stale = False
    if ym:
        months_old = (now.year - ym[0]) * 12 + (now.month - ym[1])
        if months_old >= 12:
            stale = True
            warns.append("口碑数据已超 12 个月未更新，评分/评论数不计入排序（防历史存档冒充现状）")
    if c.get("last_seen"):
        warns.append("最近一次证实营业：%s" % c["last_seen"])
    v["warnings"] = warns

    # L1 排序分：可落地度优先，口碑其次（且仅在数据新鲜时生效）。
    # 逐项留痕，供 explain 打印「到底是一票否决还是加权落后」。
    l1 = []
    score = 0.0
    base = v["confirmed"] * 10.0
    l1.append(("确认项数 %d/4 ×10" % v["confirmed"], round(base, 2)))
    score += base
    if v["operating"] == "open":
        l1.append(("营业已确认 +40（排序主键）", 40.0))
        score += 40.0
    if not stale:
        try:
            val = (float(c.get("rating")) - 7.0) * 3.0
            l1.append(("评分加权", round(val, 2)))
            score += val
        except (TypeError, ValueError):
            pass
        try:
            val = min(math.log10(int(c.get("review_count")) + 1), 4.0)
            l1.append(("评论数加权", round(val, 2)))
            score += val
        except (TypeError, ValueError):
            pass
    else:
        l1.append(("口碑超 12 个月，不计分", 0.0))
    if v["signature"] == "ok":
        l1.append(("招牌明确 +3", 3.0))
        score += 3.0
    if v["area"] == "unclear":
        l1.append(("商圈归属不明 -4", -4.0))
        score -= 4.0
    if warns:
        l1.append(("风险提示 %d 条 ×-0.5" % len(warns), round(-0.5 * len(warns), 2)))
        score -= 0.5 * len(warns)
    v["l1"] = l1
    v["score"] = round(score, 2)

    # v1.2 决策表准入：只要没被 L0 否决就进表，不再要求 status=open / 4-4 / 招牌明确。
    # 营业已确认的排在前面；未验活的标注「未验活」并排后，由用户出门前复核。
    v["decision_ready"] = not v["excluded"]
    v["needs_verify"] = v["operating"] == "unknown"
    return v


def display_name(c):
    """连锁店要带分店名，防止分店混淆。"""
    n = c.get("name") or "?"
    b = (c.get("branch") or "").strip()
    return n + ("·" + b if b and b not in n else "")


def disp_width(s):
    """终端显示宽度：中日韩全角字符按 2 列算，避免表格错位。"""
    s = str(s)
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in s)


def pad(s, width):
    s = str(s)
    return s + " " * max(0, width - disp_width(s))


# ---------------------------------------------------------------- 命令实现

def cmd_init(a):
    db = resolve_db(a.db, {"city": a.city, "area": a.area, "dish": a.dish})
    if os.path.exists(db) and not a.force:
        die("数据文件已存在：%s\n  加 --force 覆盖，或直接 add 追加候选" % db)
    data = {
        "query": {
            "city": a.city, "area": a.area, "dish": a.dish,
            "budget": a.budget, "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
        },
        "candidates": [],
    }
    save(data, db)
    print("已建立候选池：%s" % db)
    print("  城市=%s 商圈=%s 品类=%s 预算=%s" % (a.city, a.area, a.dish, a.budget or "-"))


def collect(a):
    """从参数收集候选字段，只收录显式给出的。"""
    rec = {}
    for f in FIELDS:
        val = getattr(a, f, None)
        if val is not None and val != "":
            rec[f] = val
    if "avg_price" in rec:
        try:
            rec["avg_price"] = float(rec["avg_price"])
            if rec["avg_price"] == int(rec["avg_price"]):
                rec["avg_price"] = int(rec["avg_price"])
        except ValueError:
            pass
    if "rating" in rec:
        try:
            rec["rating"] = float(rec["rating"])
        except ValueError:
            pass
    if "review_count" in rec:
        try:
            rec["review_count"] = int(rec["review_count"])
        except ValueError:
            pass
    return rec


def cmd_add(a):
    db = resolve_db(a.db)
    data = load(db)
    rec = collect(a)
    if "name" not in rec:
        die("至少需要 --name")
    if find(data, rec["name"]):
        die("候选已存在：%s\n  改字段用 update" % rec["name"])
    rec.setdefault("signature", "unknown")
    rec.setdefault("source", "manual")
    data["candidates"].append(rec)
    save(data, db)
    v = judge(rec, data["query"])
    print("已加入：%s（%s/%s 项确认，%s）" % (
        rec["name"], v["confirmed"], v["total"], v["slots"]))
    for w in v["warnings"]:
        print("  ! " + w)
    if v["excluded"]:
        print("  × 判为不推荐：" + v["exclude_reason"])


def cmd_update(a):
    db = resolve_db(a.db)
    data = load(db)
    if not a.name:
        die("需要 --name 定位候选")
    hits = find(data, a.name)
    if not hits:
        die("找不到候选：%s" % a.name)
    if len(hits) > 1:
        die("匹配到多家（%s），请写全名" % "、".join(c["name"] for _, c in hits))
    idx, cur = hits[0]
    rec = collect(a)
    rec.pop("name", None)
    cur.update(rec)
    data["candidates"][idx] = cur
    save(data, db)
    v = judge(cur, data["query"])
    print("已更新：%s（%s/%s 项确认）" % (cur["name"], v["confirmed"], v["total"]))
    for w in v["warnings"]:
        print("  ! " + w)


def cmd_list(a):
    db = resolve_db(a.db)
    data = load(db)
    q = data["query"]
    print("查询：%s %s 的 %s（预算 %s）" % (
        q.get("city"), q.get("area"), q.get("dish"), q.get("budget") or "未设"))
    if not data["candidates"]:
        print("  候选池为空")
        return
    rows = []
    for c in data["candidates"]:
        v = judge(c, q)
        rows.append([
            ("× " if v["excluded"] else "  ") + display_name(c),
            "%d/%d" % (v["confirmed"], v["total"]),
            str(c.get("rating") or "-"),
            ("￥%s" % c["avg_price"]) if c.get("avg_price") else "-",
            v["slots"],
        ])
    header = ["店名", "确认", "评分", "人均", "可去时段"]
    widths = [max(disp_width(r[i]) for r in rows + [header]) for i in range(5)]
    print("  ".join(pad(header[i], widths[i]) for i in range(5)))
    print("  ".join("-" * w for w in widths))
    for r in rows:
        print("  ".join(pad(r[i], widths[i]) for i in range(5)))


def cmd_report(a):
    db = resolve_db(a.db)
    data = load(db)
    q = data["query"]
    cands = data["candidates"]
    if not cands:
        die("候选池为空，先 add")

    judged = [(c, judge(c, q)) for c in cands]
    # v1.2 两分类：L0 一票否决出局 / 其余一律进表。
    # 排序主键 = 营业已确认(open) 优先；次键 = L1 可落地度得分。
    dropped = [(c, v) for c, v in judged if v["excluded"]]
    usable = [(c, v) for c, v in judged if not v["excluded"]]
    usable.sort(key=lambda x: (0 if x[1]["operating"] == "open" else 1,
                               -x[1]["score"]))
    verified = [(c, v) for c, v in usable if v["operating"] == "open"]
    unverified = [(c, v) for c, v in usable if v["operating"] != "open"]

    out = []
    head = "%s%s 找「%s」" % (q.get("city") or "", q.get("area") or "", q.get("dish") or "")
    out.append("## " + head)
    out.append("")
    out.append("> 全天视角：不按提问当下时刻筛，「可去时段」是覆盖表。营业已确认排前，未验活排后。")
    out.append("")

    if verified:
        best, bv = verified[0]
        out.append("**首选**：%s（%s），可去时段 %s，人均 %s；经营状态已确认（最近证实 %s）。" % (
            display_name(best), best.get("hours") or "时间未确认", bv["slots"],
            ("￥%s" % best["avg_price"]) if best.get("avg_price") else "未确认",
            best.get("last_seen") or "未填"))
    elif usable:
        out.append("**首选**：无已验活店。表内 %d 家均为「未验活」，按可落地度排序只作线索，出门前电话或登录态地图确认。" % len(usable))
    else:
        out.append("**首选**：无。%d 家候选全部被 L0 一票否决。" % len(dropped))
    out.append("")

    out.append("## 决策表（营业已确认在前）")
    out.append("")
    out.append("| 状态 | 可去时段 | 店 | 地址 | 人均 | 招牌归属 | 注意 |")
    out.append("|---|---|---|---|---|---|---|")
    if usable:
        for c, v in usable:
            st = "营业中" if v["operating"] == "open" else "未验活"
            sig = {"ok": "是", "unknown": "未确认", "mismatch": "否"}.get(v["signature"], "?")
            addr = c.get("address") or "未确认"
            if c.get("landmark"):
                addr += "（%s）" % c["landmark"]
            note = "；".join(v["warnings"][:2]) or "—"
            out.append("| %s | %s | %s | %s | %s | %s | %s |" % (
                st, v["slots"], display_name(c), addr,
                ("￥%s" % c["avg_price"]) if c.get("avg_price") else "—",
                sig, note))
    else:
        out.append("| — | — | 无可进表候选 | — | — | — | — |")
    out.append("")

    out.append("## 核验明细")
    out.append("")
    out.append("| 候选 | 来源 | 状态 | 地址 | 招牌 | 人均 | 营业 | 确认 | 评分/评论 |")
    out.append("|---|---|---|---|---|---|---|---|---|")
    stmap = {"open": "营业中", "closed": "已闭店", "elsewhere": "异地", "unknown": "未确认"}
    for c, v in usable:
        # 用 GBK 也能编码的符号（对勾/叉号在 GBK 环境下会抛 UnicodeEncodeError）
        sym = {"ok": "√", "partial": "~", "missing": "×"}
        sig = {"ok": "√", "unknown": "?", "mismatch": "×"}
        out.append("| %s | %s | %s | %s | %s | %s | %s | %d/4 | %s |" % (
            display_name(c), c.get("source") or "—",
            stmap.get(v["operating"], "?"),
            sym.get(v["address"], "?"), sig.get(v["signature"], "?"),
            sym.get(v["price"], "?"), sym.get(v["hours"], "?"),
            v["confirmed"],
            ("%s / %s条" % (c["rating"], c["review_count"]))
            if c.get("rating") and c.get("review_count") else "—"))
    out.append("")

    if dropped:
        out.append("## 没排上的 & 为什么（L0 一票否决）")
        out.append("")
        out.append("| 候选 | 闸门类型 | 依据 |")
        out.append("|---|---|---|")
        for c, v in dropped:
            types = "、".join(g[0] for g in v["gates"]) or "—"
            detail = "；".join(g[1] for g in v["gates"]) or v["exclude_reason"]
            out.append("| %s | %s | %s |" % (display_name(c), types, detail))
        out.append("")

    # 「最近一次证实营业」是中性证据，不是待办；别把已验活店塞进待人工确认区。
    def real_warns(v):
        return [w for w in v["warnings"] if not w.startswith("最近一次证实营业")]

    warn_only = [(c, v) for c, v in verified if real_warns(v)]
    if unverified or warn_only:
        out.append("## 待人工确认（已进表，排后）")
        out.append("")
        for c, v in unverified:
            out.append("- **%s**：经营状态未确认，出门前电话或登录态地图验活；%s" % (
                display_name(c), "；".join(real_warns(v)) or "其余项已核"))
        for c, v in warn_only:
            out.append("- **%s**：%s" % (display_name(c), "；".join(real_warns(v))))
        out.append("")

    text = "\n".join(out)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        print("已写入 %s" % os.path.abspath(a.out))
    print(text)


def cmd_explain(a):
    """打印单店的 L0 闸门 / L1 加权分解，验证「一票否决」没被口碑分赎回。"""
    db = resolve_db(a.db)
    data = load(db)
    if not a.name:
        die("需要 --name 定位候选")
    hits = find(data, a.name)
    if not hits:
        die("找不到候选：%s" % a.name)
    if len(hits) > 1:
        die("匹配到多家（%s），请写全名" % "、".join(c["name"] for _, c in hits))
    c = hits[0][1]
    v = judge(c, data["query"])
    stmap = {"open": "营业中", "closed": "已闭店", "elsewhere": "异地", "unknown": "未确认"}

    print("候选：%s" % display_name(c))
    print("第 0 项经营状态：%s（status=%s）" % (
        stmap.get(v["operating"], "?"), c.get("status") or "未填"))
    print("四项硬核验：地址=%s 招牌=%s 人均=%s 营业=%s → %d/4" % (
        v["address"], v["signature"], v["price"], v["hours"], v["confirmed"]))
    print()
    if v["gates"]:
        print("[L0 一票否决] 命中 %d 条闸门，直接出局：" % len(v["gates"]))
        for t, d in v["gates"]:
            print("  × %s — %s" % (t, d))
    else:
        print("[L0 一票否决] 未命中，放行到 L1")
    print()
    if v["excluded"]:
        print("[L1 加权排序] 不计算 —— 闸门不可被评分/评论数赎回")
    else:
        print("[L1 加权排序]")
        for label, val in v["l1"]:
            print("  %s %+7.2f" % (pad(label, 32), val))
        print("  %s %7.2f" % (pad("= score", 32), v["score"]))
    print()
    print("决策表准入：L0 未命中 %s ｜ 经营状态 %s（只影响排序，不做闸门）" % (
        "√" if not v["excluded"] else "×",
        "已确认" if v["operating"] == "open" else "未验活"))
    if v["excluded"]:
        verdict = "出局，进「没排上的」（L0 一票否决）"
    elif v["operating"] == "open":
        verdict = "进决策表，排在「营业已确认」组"
    else:
        verdict = "进决策表，排在「未验活」组（需电话或地图复核）"
    print("→ " + verdict)
    for w in v["warnings"]:
        print("  ! " + w)


# ---------------------------------------------------------------- CLI

def build_parser():
    p = argparse.ArgumentParser(
        description="workbuddy-food 候选池管理：硬核验判定 + 全天决策表（v1.2 营业已确认优先）")
    p.add_argument("--db", help="数据文件路径（默认 .food-radar/<城市_商圈_品类>.json）")
    sub = p.add_subparsers(dest="cmd")

    def add_fields(sp):
        sp.add_argument("--db", default=argparse.SUPPRESS,
                        help="数据文件路径（放在子命令后也可）")
        sp.add_argument("--name")
        sp.add_argument("--branch", help="分店名，连锁必填")
        sp.add_argument("--address", help="精确到门牌")
        sp.add_argument("--landmark", help="参照物，如'紫丹阁对面'")
        sp.add_argument("--avg-price", dest="avg_price")
        sp.add_argument("--hours", help="如 07:00-22:30 / 17:00-02:00 / 全天")
        sp.add_argument("--rating")
        sp.add_argument("--review-count", dest="review_count")
        sp.add_argument("--signature", choices=["yes", "no", "unknown"],
                        help="目标菜是否为该店招牌")
        sp.add_argument("--signature-note", dest="signature_note")
        sp.add_argument("--source", help="候选来源：deepseek/元宝/豆包/大众点评/用户")
        sp.add_argument("--data-date", dest="data_date", help="数据时点，如 2026-10")
        sp.add_argument("--area-confirmed", dest="area_confirmed", default=None,
                        action="store_const", const=True,
                        help="人工已确认该店在本商圈，消除异地嫌疑提示")
        sp.add_argument("--status", choices=["open", "closed", "unknown", "elsewhere"],
                        help="经营状态：open 排最前；unknown 仍进表但标未验活并排后；closed/elsewhere 一票否决")
        sp.add_argument("--last-seen", dest="last_seen", help="最近一次证实营业的时点")
        sp.add_argument("--note")

    sp = sub.add_parser("init", help="建立候选池")
    sp.add_argument("--db", default=argparse.SUPPRESS)
    sp.add_argument("--city", required=True)
    sp.add_argument("--area", required=True)
    sp.add_argument("--dish", required=True)
    sp.add_argument("--budget")
    sp.add_argument("--force", action="store_true")
    sp.set_defaults(func=cmd_init)

    sp = sub.add_parser("add", help="加入候选")
    add_fields(sp)
    sp.set_defaults(func=cmd_add)

    sp = sub.add_parser("update", help="更新候选字段")
    add_fields(sp)
    sp.set_defaults(func=cmd_update)

    sp = sub.add_parser("list", help="候选池概览")
    sp.add_argument("--db", default=argparse.SUPPRESS)
    sp.set_defaults(func=cmd_list)

    sp = sub.add_parser("explain", help="打印单店的 L0 一票否决 / L1 加权分解")
    sp.add_argument("--db", default=argparse.SUPPRESS)
    sp.add_argument("--name", required=True)
    sp.set_defaults(func=cmd_explain)

    sp = sub.add_parser("report", help="出决策表")
    sp.add_argument("--db", default=argparse.SUPPRESS)
    sp.add_argument("--out", help="同时写入 markdown 文件")
    sp.set_defaults(func=cmd_report)

    return p


def main():
    p = build_parser()
    a = p.parse_args()
    if not a.cmd:
        p.print_help()
        return
    a.func(a)


if __name__ == "__main__":
    main()
