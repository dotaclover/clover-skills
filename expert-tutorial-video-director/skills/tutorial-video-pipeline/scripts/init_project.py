# -*- coding: utf-8 -*-
"""系列教程视频：项目骨架初始化。

用法：
    python init_project.py --root <项目目录> --title "AI 实战课" --episodes 6

产物：
    <root>/series.json                 全系列配置（风格、音色、固定开头结尾、分集表）
    <root>/assets/cards/               跨集共用卡片（片头/结束/作业黑板模板）
    <root>/episodes/EP01/beats.json    单集分镜+台词（待填）
    <root>/episodes/EP01/{cards,cards_png,rec,build,out}/
"""
import argparse
import json
from pathlib import Path

BASE_CARD = """<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" viewBox="0 0 1920 1080">
  <title>{title}</title>
  <rect x="0" y="0" width="1920" height="1080" fill="#121A14"/>

  <g fill="none" stroke="#6F8F5A" stroke-width="2" opacity="0.9">
    <path d="M150 150 C124 142 124 108 150 96 C176 108 176 142 150 150 Z" transform="rotate(45 150 150)"/>
    <path d="M150 150 C124 142 124 108 150 96 C176 108 176 142 150 150 Z" transform="rotate(135 150 150)"/>
    <path d="M150 150 C124 142 124 108 150 96 C176 108 176 142 150 150 Z" transform="rotate(225 150 150)"/>
    <path d="M150 150 C124 142 124 108 150 96 C176 108 176 142 150 150 Z" transform="rotate(315 150 150)"/>
  </g>

  <text x="225" y="178" font-family="Source Han Sans SC, Microsoft YaHei, sans-serif" font-size="72" font-weight="500" letter-spacing="8" fill="#EDEAE0">{heading}</text>
  <text x="1785" y="170" text-anchor="end" font-family="Microsoft YaHei, sans-serif" font-size="34" letter-spacing="3" fill="#6F8F5A">{series}</text>
  <line x1="0" y1="238" x2="1920" y2="238" stroke="#2E3B2E" stroke-width="2"/>

  <text x="960" y="660" text-anchor="middle" font-family="Microsoft YaHei, sans-serif" font-size="48" fill="#EDEAE0">{line1}</text>
</svg>
"""

BEATS_TMPL = {
    "episode": "EP01",
    "title": "[TODO] 本集标题",
    "canvas": {"width": 1920, "height": 1080, "fps": 30},
    "voice": {"name": "zh-CN-YunxiNeural", "rate": "+8%", "volume": "+0%"},
    "loudnorm": "loudnorm=I=-16:TP=-1.5:LRA=11",
    "card_tail": 0.9,
    "cards_dir": "cards",
    "cards_png_dir": "cards_png",
    "rec_dir": "rec",
    "beats": [
        {"id": "c01", "kind": "card", "png": "C01_片头.png",
         "text": "[TODO] 本集一句话钩子。同一份材料，交给 A 和 B 各做一次。"},
        {"id": "w1", "kind": "demo", "src": "demo.mp4", "start": 0.0, "end": 6.0, "speed": 1.5,
         "text": "[TODO] 对着画面说画面里正在发生的事，不念功能表。"},
        {"id": "c99", "kind": "card", "png": "C99_结束卡.png",
         "text": "我是顺哥，我们下个视频见。"}
    ]
}

SERIES_TMPL = {
    "series": "[TODO] 系列名",
    "audience": "[TODO] 谁在看，基础到什么程度",
    "promise": "[TODO] 看完能做什么，一句话",
    "style": {
        "canvas": "1920x1080",
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="项目根目录")
    ap.add_argument("--title", default="[TODO] 系列名")
    ap.add_argument("--episodes", type=int, default=1)
    a = ap.parse_args()

    root = Path(a.root)
    (root / "assets/cards").mkdir(parents=True, exist_ok=True)

    series = json.loads(json.dumps(SERIES_TMPL))
    series["series"] = a.title
    for i in range(1, a.episodes + 1):
        ep = "EP%02d" % i
        series["episodes"].append({"id": ep, "title": "[TODO]", "goal": "[TODO]", "status": "planned"})

    for name, heading, line in [
        ("C01_片头.svg", "系列片头", "[TODO] 主标题"),
        ("C99_结束卡.svg", "结束卡", "我是顺哥，我们下个视频见。"),
        ("C08_课后作业.svg", "课后作业", "[TODO] 作业题"),
    ]:
        p = root / "assets/cards" / name
        if not p.exists():
            p.write_text(BASE_CARD.format(title=name[:-4], heading=heading,
                                          series=a.title, line1=line), encoding="utf-8")

    for i in range(1, a.episodes + 1):
        ep_dir = root / "episodes" / ("EP%02d" % i)
        for d in ("cards", "cards_png", "rec", "build", "out"):
            (ep_dir / d).mkdir(parents=True, exist_ok=True)
        b = ep_dir / "beats.json"
        if not b.exists():
            t = json.loads(json.dumps(BEATS_TMPL))
            t["episode"] = "EP%02d" % i
            b.write_text(json.dumps(t, ensure_ascii=False, indent=2), encoding="utf-8")

    sp = root / "series.json"
    if not sp.exists():
        sp.write_text(json.dumps(series, ensure_ascii=False, indent=2), encoding="utf-8")

    print("已初始化:", root)
    print("  series.json ->", sp)
    print("  assets/cards -> 片头/结束/作业 三张基础卡")
    print("  episodes/EP01..EP%02d -> beats.json + cards/cards_png/rec/build/out" % a.episodes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
