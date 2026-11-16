#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""单件经济模型与三档情景测算（阶段 3 成本粗算 / 阶段 9 财务复核）。

为什么要有这个脚本：
    技能自己的规则写着「禁止让模型心算百分比、盈亏平衡」，那么测算就不能靠
    对话里的心算完成。所有除法、取整、情景叠加都走这里。

用法（示例见 --help）：
    python calc_unit_economics.py --price 199 --cogs 70 --commission 5 \
        --payment 0.6 --shipping 8 --return-rate 8 --ads-pct 20 \
        --fixed 12000 --volume 200

输出：
    1. 成本结构表（每项金额 + 占售价比例）
    2. 贡献毛利 / 毛利率 / 盈亏平衡月销量 / 安全边际
    3. 三档情景：客流 -30%、成本 +20%、两者同时
    4. 可直接粘贴进 03_六维对比与测算.md 的片段
    5. 可直接粘贴进 98_证据台账.md 的一行（含公式与证据级别）

不加 --quiet 时会同时打印档案片段；--json 输出结构化结果。
"""

import argparse
import json
import math
import sys
from datetime import date

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

SCORE_BY_LEVEL = {"L1": 9, "L2": 8, "L3": 6, "L4": 5, "L5": 3}


def money(x):
    return round(x + 0.0, 2)


def build_model(a):
    """把输入折算成单件成本结构与单位贡献。"""
    p = a.price
    commission = p * a.commission / 100.0
    payment = p * a.payment / 100.0
    ads = p * a.ads_pct / 100.0 + a.ads_fixed

    # 退货损耗：往返运费 + 商品折损（默认 10%）× 退货率。
    # 平台佣金若退还则不计；若不退还，请把差额补进 --cogs 或 --commission。
    return_loss = a.return_rate / 100.0 * (2 * a.shipping + 0.1 * a.cogs)

    items = [
        ("进货 / 生产成本", a.cogs, "变动"),
        ("平台佣金", commission, "按售价"),
        ("支付手续费", payment, "按售价"),
        ("推广费", ads, "按售价 + 固定"),
        ("物流包装", a.shipping, "每单"),
        ("退货损耗", return_loss, "按退货率折算"),
    ]
    vc = sum(x for _, x, _ in items)
    cm = p - vc
    margin = cm / p if p else 0.0
    return {
        "price": p,
        "items": items,
        "vc": vc,
        "cm": cm,
        "margin": margin,
        "fixed": a.fixed,
        "volume": a.volume,
    }


def breakeven(m):
    """盈亏平衡月销量；单位贡献 <= 0 时不可能平衡。"""
    if m["cm"] <= 0:
        return None
    if m["fixed"] <= 0:
        return 0
    return math.ceil(m["fixed"] / m["cm"])


def scenario(a, price_mult=1.0, cogs_mult=1.0, ship_mult=1.0, vol_mult=1.0):
    """按倍数扰动后重算，返回该情景的关键指标。"""
    p = a.price * price_mult
    cogs = a.cogs * cogs_mult
    ship = a.shipping * ship_mult
    commission = p * a.commission / 100.0
    payment = p * a.payment / 100.0
    ads = p * a.ads_pct / 100.0 + a.ads_fixed
    return_loss = a.return_rate / 100.0 * (2 * ship + 0.1 * cogs)
    vc = cogs + commission + payment + ads + ship + return_loss
    cm = p - vc
    vol = a.volume * vol_mult
    profit = vol * cm - a.fixed
    return {
        "price": p,
        "cm": cm,
        "margin": cm / p if p else 0.0,
        "volume": vol,
        "profit": profit,
        "alive": profit >= 0,
    }


def risks(m, qstar):
    out = []
    if m["cm"] <= 0:
        out.append(("严重", "单件贡献毛利 <= 0：卖一件亏一件，先改定价或成本结构，不要继续往下做。"))
        out.append(("注意", "此时「客流 −30%」的净利会比基准好看，因为每单都亏、卖得少亏得少；这不是好转，是错觉。"))
        return out
    if m["margin"] < 0.40:
        out.append(("高", "毛利率 {:.1f}%，低于 40% 警戒线；抗降价与抗退货能力弱。".format(m["margin"] * 100)))
    if qstar is not None and m["volume"] > 0:
        if qstar > m["volume"]:
            out.append(("高", "盈亏平衡需 {} 件/月，当前按 {} 件/月测算，尚未打平。".format(qstar, int(m["volume"]))))
        else:
            sa = (m["volume"] - qstar) / m["volume"]
            if sa < 0.20:
                out.append(("中", "安全边际仅 {:.0f}%：销量掉两成就转亏。".format(sa * 100)))
    return out


def fmt_table(m):
    lines = ["| 项目 | 金额（元） | 占售价 | 口径 |", "|---|---:|---:|---|"]
    for name, val, basis in m["items"]:
        pct = (val / m["price"] * 100) if m["price"] else 0
        lines.append("| {} | {:.2f} | {:.1f}% | {} |".format(name, val, pct, basis))
    lines.append("| **变动成本合计** | **{:.2f}** | **{:.1f}%** | |".format(m["vc"], m["vc"] / m["price"] * 100 if m["price"] else 0))
    lines.append("| **单件贡献毛利** | **{:.2f}** | **{:.1f}%** | 售价 − 变动成本 |".format(m["cm"], m["margin"] * 100))
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(
        description="单件经济模型与三档情景测算（不经模型心算）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例：
  python calc_unit_economics.py --price 199 --cogs 70 --commission 5 \\
      --payment 0.6 --shipping 8 --return-rate 8 --ads-pct 20 \\
      --fixed 12000 --volume 200 --level L3
""",
    )
    ap.add_argument("--price", type=float, required=True, help="售价（元）")
    ap.add_argument("--cogs", type=float, required=True, help="进货或生产成本（元/件）")
    ap.add_argument("--commission", type=float, default=5.0, help="平台佣金率 %%，默认 5")
    ap.add_argument("--payment", type=float, default=0.6, help="支付手续费率 %%，默认 0.6")
    ap.add_argument("--shipping", type=float, default=0.0, help="物流包装成本（元/单）")
    ap.add_argument("--return-rate", type=float, default=0.0, help="退货率 %%，默认 0")
    ap.add_argument("--ads-pct", type=float, default=0.0, help="推广费占售价比 %%，默认 0")
    ap.add_argument("--ads-fixed", type=float, default=0.0, help="推广费（元/单），默认 0")
    ap.add_argument("--fixed", type=float, default=0.0, help="月固定成本（房租/人工/软件等）")
    ap.add_argument("--volume", type=float, default=0.0, help="预计月销量（件）")
    ap.add_argument("--level", default="L4", choices=list(SCORE_BY_LEVEL), help="输入数据的取证级别，默认 L4")
    ap.add_argument("--json", action="store_true", help="额外输出 JSON")
    ap.add_argument("--quiet", action="store_true", help="不打印可粘贴片段")

    a = ap.parse_args()

    if a.price <= 0:
        ap.error("--price 必须大于 0")
    if a.cogs < 0 or a.shipping < 0 or a.fixed < 0 or a.volume < 0:
        ap.error("成本与销量不能为负")
    for name, v in (("--commission", a.commission), ("--payment", a.payment),
                    ("--ads-pct", a.ads_pct), ("--return-rate", a.return_rate)):
        if not 0 <= v <= 100:
            ap.error("{} 应在 0–100 之间".format(name))

    m = build_model(a)
    qstar = breakeven(m)
    profit = a.volume * m["cm"] - a.fixed if a.volume else None
    safety = ((a.volume - qstar) / a.volume) if (a.volume and qstar is not None) else None

    base = scenario(a)
    s_flow = scenario(a, vol_mult=0.7)
    s_cost = scenario(a, cogs_mult=1.2, ship_mult=1.2)
    s_both = scenario(a, cogs_mult=1.2, ship_mult=1.2, vol_mult=0.7)

    print("## 单件经济模型")
    print()
    print("> 售价 {:.2f} 元；月固定成本 {:.0f} 元；测算销量 {:.0f} 件/月；输入级别 {}。".format(
        a.price, a.fixed, a.volume, a.level))
    print()
    print(fmt_table(m))
    print()
    print("## 关键指标")
    print()
    print("| 指标 | 数值 | 说明 |")
    print("|---|---:|---|")
    print("| 单件贡献毛利 | {:.2f} 元 | 每卖一件能拿去覆盖固定成本的钱 |".format(m["cm"]))
    print("| 毛利率 | {:.1f}% | 低于 40% 需明确提示风险 |".format(m["margin"] * 100))
    if qstar is None:
        print("| 盈亏平衡月销量 | 无法平衡 | 单件贡献 <= 0 |")
    else:
        print("| 盈亏平衡月销量 | {} 件 | 向上取整 |".format(qstar))
    if profit is not None:
        print("| 当前销量月净利 | {:.2f} 元 | 销量 × 贡献毛利 − 固定成本 |".format(profit))
    if safety is not None:
        print("| 安全边际 | {:.1f}% | 销量可下滑的空间 |".format(safety * 100))
    print()

    print("## 三档情景")
    print()
    print("| 情景 | 贡献毛利 | 毛利率 | 月净利 | 是否活着 |")
    print("|---|---:|---:|---:|---|")
    for label, s in (("基准", base), ("客流 −30%", s_flow),
                     ("成本 +20%", s_cost), ("两者同时", s_both)):
        print("| {} | {:.2f} | {:.1f}% | {:.2f} | {} |".format(
            label, s["cm"], s["margin"] * 100, s["profit"], "是" if s["alive"] else "**否**"))
    print()

    rr = risks(m, qstar)
    print("## 风险判定")
    print()
    if rr:
        for level, text in rr:
            print("- **{}**：{}".format(level, text))
    else:
        print("- 未触发内置风险条件；仍需人工核对输入真实性。")
    print()

    if not a.quiet:
        sc = SCORE_BY_LEVEL.get(a.level, 5)
        formula = ("贡献毛利 = 售价 − (进货 + 售价×(佣金率+支付费率+推广率) + 推广固定 + 履约 + 退货率×(2×履约+0.1×进货))")
        inputs = "售价 {p}；进货 {c}；佣金 {k}%；支付 {pay}%；履约 {s}；退货 {r}%；推广 {ap}%+{af}元/单；固定 {f}".format(
            p=a.price, c=a.cogs, k=a.commission, pay=a.payment, s=a.shipping,
            r=a.return_rate, ap=a.ads_pct, af=a.ads_fixed, f=a.fixed)
        print("---")
        print()
        print("### 可直接粘贴到 98_证据台账.md 的一行")
        print()
        print("| E-新增 | 单件贡献毛利 {:.2f} 元；盈亏平衡 {} 件/月 | {} | 公式：{}；输入：{} | {} | {}/10 | 未验证 | 阶段 3 测算 | 核实进货价与类目佣金率 |".format(
            m["cm"], "无法平衡" if qstar is None else qstar, a.level, formula, inputs,
            date.today().isoformat(), sc))
        print()
        print("> 证据级别填 {}，建议分 {}。若进货价、佣金率均已回一手页面核实，可上调至 L2（8 分）。".format(a.level, sc))

    if a.json:
        payload = {
            "input": vars(a),
            "unit": {"vc": money(m["vc"]), "cm": money(m["cm"]), "margin": round(m["margin"], 4)},
            "breakeven_volume": qstar,
            "net_profit": money(profit) if profit is not None else None,
            "safety_margin": round(safety, 4) if safety is not None else None,
            "scenarios": {
                "base": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in base.items()},
                "flow_minus_30": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in s_flow.items()},
                "cost_plus_20": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in s_cost.items()},
                "both": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in s_both.items()},
            },
        }
        print()
        print("### JSON")
        print()
        print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
