# -*- coding: utf-8 -*-
"""系列教程视频：项目骨架初始化。

用法：
    python init_project.py --root <项目目录> --title "AI 实战课" --episodes 6
    python init_project.py --root <项目目录> --title "竖屏版" --preset 9:16 --episodes 3

产物：
    <root>/series.json                 全系列配置（风格、音色、固定开头结尾、分集表）
    <root>/assets/cards/               跨集共用卡片（片头/结束/作业模板，按画布尺寸生成）
    <root>/episodes/EP01/beats.json    单集分镜+台词（待填）
    <root>/episodes/EP01/{cards,cards_png,rec,build,out}/
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))          # 本技能自带 canvas.py，不依赖任何其他技能
try:
    import canvas as canvas_mod
except Exception:
    canvas_mod = None

CARD = """<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
  <title>{title}</title>
  <rect x="0" y="0" width="{w}" height="{h}" fill="#121A14"/>

  <g fill="none" stroke="#6F8F5A" stroke-width="{sw}" opacity="0.9"
     transform="translate({sx},{sy}) scale({cs}) translate(-150,-150)">
    <path d="M150 150 C124 142 124 108 150 96 C176 108 176 142 150 150 Z" transform="rotate(45 150 150)"/>
    <path d="M150 150 C124 142 124 108 150 96 C176 108 176 142 150 150 Z" transform="rotate(135 150 150)"/>
    <path d="M150 150 C124 142 124 108 150 96 C176 108 176 142 150 150 Z" transform="rotate(225 150 150)"/>
    <path d="M150 150 C124 142 124 108 150 96 C176 108 176 142 150 150 Z" transform="rotate(315 150 150)"/>
  </g>

  <text x="{hx}" y="{hy}" font-family="Source Han Sans SC, Microsoft YaHei, sans-serif"
        font-size="{t_card}" font-weight="500" letter-spacing="{ls}" fill="#EDEAE0">{heading}</text>
  <text x="{rx}" y="{ry}" text-anchor="end" font-family="Microsoft YaHei, sans-serif"
        font-size="{t_label}" letter-spacing="3" fill="#6F8F5A">{series}</text>
  <line x1="0" y1="{ly}" x2="{w}" y2="{ly}" stroke="#2E3B2E" stroke-width="{sw}"/>

  <text x="{cx}" y="{y1}" text-anchor="middle" font-family="Source Han Sans SC, Microsoft YaHei, sans-serif"
        font-size="{t_title}" font-weight="500" fill="#EDEAE0">{line1}</text>
  <text x="{cx}" y="{y2}" text-anchor="middle" font-family="Microsoft YaHei, sans-serif"
        font-size="{t_sub}" fill="#97A38F">{line2}</text>
  <text x="{cx}" y="{y3}" text-anchor="middle" font-family="Microsoft YaHei, sans-serif"
        font-size="{t_note}" fill="#D8A73C">{series}</text>
</svg>
"""

BEATS = {
    "episode": "EP01",
    "title": "[TODO] 本集标题",
    "canvas": {"preset": "16:9", "fps": 30},
    "voice": {"name": "zh-CN-YunxiNeural", "rate": "+8%", "volume": "+0%"},
    "loudnorm": "loudnorm=I=-16:TP=-1.5:LRA=11",
    "card_tail": 0.9,
    "cards_dir": "cards",
    "cards_png_dir": "cards_png",
    "rec_dir": "rec",
    "beats": [
        {"id": "c01", "kind": "card", "png": "C01_片头.png",
         "text": "[TODO] 本集一句话钩子。同一份材料，交给 A 和 B 各做一次。"},
        {"id": "w1", "kind": "demo", "src": "demo.mp4", "start": 0.0, "end": 6.0,
         "speed": 1.5, "text": "[TODO] 对着画面说画面里正在发生的事，不念功能表。"},
        {"id": "c99", "kind": "card", "png": "C99_结束卡.png",
         "text": "我是顺哥，我们下个视频见。"}
    ]
}

SERIES = {
    "series": "[TODO] 系列名",
    "audience": "[TODO] 谁在看，基础到什么程度",
    "promise": "[TODO] 看完能做什么，一句话",
    "style": {
        "canvas": {"preset": "16:9", "fps": 30},
        "palette": {"bg": "#121A14", "text": "#EDEAE0", "muted": "#97A38F",
                    "accent": "#6F8F5A", "gold": "#D8A73C", "line": "#2E3B2E"},
        "font": "Source Han Sans SC, Microsoft YaHei, sans-serif",
        "voice": "zh-CN-YunxiNeural",
        "rate": "+8%",
        "loudnorm": "loudnorm=I=-16:TP=-1.5:LRA=11"
    },
    "fixed_open": "大家好，我是 Clover，你们也可以叫我顺哥。",
    "fixed_close": "我是顺哥，我们下个视频见。",
    "episodes": []
}


def tokens(w, h):
    if canvas_mod:
        return canvas_mod.tokens(w, h)
    u = min(w, h) / 1080.0
    return {"unit": u, "title": int(108 * u), "card_title": int(72 * u),
            "body": int(48 * u), "sub": int(40 * u), "note": int(34 * u),
            "label": int(30 * u), "safe_x": int(135 * u), "safe_y": int(120 * u),
            "gap": int(64 * u), "width": w, "height": h}


def card_svg(title, heading, series, line1, w, h, line2="[TODO] 副标题"):
    t = tokens(w, h)
    u = t["unit"]
    sx, sy = t["safe_x"], t["safe_y"]
    y1 = int(h * 0.46)
    return CARD.format(
        w=w, h=h, title=title, series=series, heading=heading,
        line1=line1, line2=line2,
        sx=sx, sy=sy, cs=round(0.5 * u, 3), sw=max(1, round(2 * u)),
        hx=sx + int(90 * u), hy=sy + int(58 * u),
        t_card=t["card_title"], ls=max(1, int(8 * u)),
        rx=w - sx, ry=sy + int(50 * u), t_label=t["label"],
        ly=sy + int(118 * u),
        cx=w // 2, y1=y1, y2=y1 + int(82 * u), y3=int(h * 0.90),
        t_title=t["title"], t_sub=t["sub"], t_note=t["note"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="项目根目录")
    ap.add_argument("--title", default="[TODO] 系列名")
    ap.add_argument("--preset", default="16:9",
                    help="画布：16:9 / 9:16 / 1:1 / 4:5 / 3:4 / 4k")
    ap.add_argument("--size", help="自定义画布，如 1440x1080（覆盖 --preset）")
    ap.add_argument("--episodes", type=int, default=1)
    a = ap.parse_args()

    if canvas_mod:
        w, h = canvas_mod.parse_size(a.size) if a.size else canvas_mod.resolve({"preset": a.preset})
        desc = canvas_mod.describe(w, h)
    else:
        w, h = (1920, 1080)
        desc = "1920×1080（canvas.py 未加载，退回默认）"

    root = Path(a.root)
    (root / "assets/cards").mkdir(parents=True, exist_ok=True)

    series = json.loads(json.dumps(SERIES))
    series["series"] = a.title
    series["style"]["canvas"] = {"preset": a.preset if not a.size else "custom",
                                 "width": w, "height": h, "fps": 30}
    for i in range(1, a.episodes + 1):
        series["episodes"].append({"id": "EP%02d" % i, "title": "[TODO]",
                                   "goal": "[TODO]", "status": "planned"})

    for name, heading, line in [
        ("C01_片头.svg", "系列片头", "[TODO] 主标题"),
        ("C99_结束卡.svg", "结束卡", "我是顺哥，我们下个视频见。"),
        ("C08_课后作业.svg", "课后作业", "[TODO] 作业题"),
    ]:
        p = root / "assets/cards" / name
        if not p.exists():
            p.write_text(card_svg(name[:-4], heading, a.title, line, w, h), encoding="utf-8")

    for i in range(1, a.episodes + 1):
        ep_dir = root / "episodes" / ("EP%02d" % i)
        for d in ("cards", "cards_png", "rec", "build", "out"):
            (ep_dir / d).mkdir(parents=True, exist_ok=True)
        b = ep_dir / "beats.json"
        if not b.exists():
            t = json.loads(json.dumps(BEATS))
            t["episode"] = "EP%02d" % i
            t["canvas"] = {"preset": a.preset if not a.size else "custom",
                           "width": w, "height": h, "fps": 30}
            b.write_text(json.dumps(t, ensure_ascii=False, indent=2), encoding="utf-8")

    sp = root / "series.json"
    if not sp.exists():
        sp.write_text(json.dumps(series, ensure_ascii=False, indent=2), encoding="utf-8")

    print("已初始化:", root)
    print("  画布:", desc)
    print("  series.json ->", sp)
    print("  assets/cards -> 片头/结束/作业 三张基础卡（%d×%d）" % (w, h))
    print("  episodes/EP01..EP%02d -> beats.json + cards/cards_png/rec/build/out" % a.episodes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
