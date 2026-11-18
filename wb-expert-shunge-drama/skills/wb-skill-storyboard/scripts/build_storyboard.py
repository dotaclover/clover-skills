#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_storyboard.py — 由 spec JSON 生成 Seedance 分镜交付物。

输入：符合 references/storyboard_schema.md 的 spec JSON
输出：
  - <name>.md    可读分镜表（含人物三视图定妆 + 分镜明细 + 提示词清单）
  - <name>.json  规范化后的结构化数据（便于接入生成流水线）
  - <name>.xlsx  Excel 分镜表（总览 / 人物定妆 / 分镜表 三张 sheet，带表头样式与自动换行）

自动补全（无需手抄，可被手写字段覆盖）：
  - 若某分镜缺 prompt，按公式从 anchor/motion/camera/lighting/style/quality 自动拼装。
  - 若某角色缺 three_view，按 anchor_phrase 自动生成 正/侧/背 三视图定妆提示词。

质量自检（程序化落地 SKILL.md 的交付前清单）：
  - anchor phrase 是否逐字一致（与各角色 anchor_phrase 完全相等才安全）。
  - 单镜时长是否超当前型号上限（2.0 系列 15s / 2.5 为 30s）或低于 4s。
  - 单镜头是否只含一种运动（camera 字段出现多个运动词则告警）。
  - 是否缺 audio / cost_note / prompt_zh（按需）。

可选增强：
  - 每镜可附 prompt_zh（中文最终提示词）；存在时 Markdown 与 Excel 同时渲染英文+中文两版。
  - --pure-zh：额外产出 <name>_纯中文.md / <name>_纯中文.xlsx（全中文，仅中文提示词；
               anchor phrase 作为固定身份令牌保留英文并在角色区注明）。
  - --check：仅做校验与自检报告，不写文件（CI / 交付前快速体检）。
  - --no-auto：关闭自动拼装与三视图自动生成（完全按手填内容输出）。
"""

import argparse
import json
import os
import re
import sys


# ---------------- 自动拼装与生成 ----------------

def assemble_prompt(shot):
    """按公式从结构化字段拼出 Seedance 提示词；任一字段缺失则跳过。"""
    parts = []
    if shot.get("anchor"):
        parts.append(shot["anchor"].strip().rstrip("."))
    if shot.get("motion"):
        parts.append(shot["motion"].strip().rstrip("."))
    if shot.get("camera"):
        parts.append(shot["camera"].strip().rstrip("."))
    if shot.get("lighting"):
        parts.append(shot["lighting"].strip().rstrip("."))
    if shot.get("style"):
        parts.append(shot["style"].strip().rstrip("."))
    if shot.get("quality"):
        parts.append(shot["quality"].strip().rstrip("."))
    if not parts:
        return ""
    return ". ".join(parts) + "."


def auto_three_view(anchor_phrase):
    """按 anchor_phrase 生成 正/侧/背 三视图定妆提示词。"""
    base = (anchor_phrase or "").strip().rstrip(".")
    if not base:
        return {}
    return {
        "front": (
            f"Character turnaround sheet, front view of {base}, full body, "
            f"neutral standing pose, plain neutral grey background, soft studio light, "
            f"clean commercial style, high detail, sharp focus, no text, no logo."
        ),
        "side": (
            f"Character turnaround sheet, side profile view of {base}, full body, "
            f"neutral standing pose, plain neutral grey background, soft studio light, "
            f"clean commercial style, high detail, sharp focus, no text, no logo."
        ),
        "back": (
            f"Character turnaround sheet, back view of {base}, full body, "
            f"neutral standing pose, plain neutral grey background, soft studio light, "
            f"clean commercial style, high detail, sharp focus, no text, no logo."
        ),
    }


def enrich_spec(spec, auto=True):
    """就地补全 prompt 与 three_view（仅当缺失时），返回补全记录。"""
    log = {"prompts_assembled": [], "three_view_generated": []}
    if not auto:
        return log
    for c in spec.get("characters", []):
        if not c.get("three_view") and c.get("anchor_phrase"):
            c["three_view"] = auto_three_view(c["anchor_phrase"])
            log["three_view_generated"].append(c.get("name", c.get("id", "?")))
    for s in spec.get("shots", []):
        if not s.get("prompt"):
            p = assemble_prompt(s)
            if p:
                s["prompt"] = p
                log["prompts_assembled"].append(s.get("shot_id", "?"))
    return log


# ---------------- 校验与自检 ----------------

# 镜头运动关键词（用于「单镜头单运动」启发式检测，按单词边界匹配）
MOTION_PATTERNS = {
    "push": r"\bpush[- ]?in\b",
    "pull": r"\bpull[- ]?back\b",
    "pan": r"\bpan\b",
    "tilt": r"\btilt\b",
    "orbit": r"\borbit\b",
    "tracking": r"\btracking\b",
    "crane": r"\bcrane\b",
    "dolly": r"\bdolly\b",
    "handheld": r"\bhandheld\b",
    "static": r"\bstatic\b",
    "aerial": r"\baerial\b",
}
# 单条时长上限按目标型号取（事实源：seedance-dev/references/legacy-seedance-video.md）
MODEL_DURATION_LIMIT = {
    "2.5": 30,
    "2.0": 15,
    "2.0-fast": 15,
    "2.0-mini": 15,
}
MIN_DURATION = 4          # 短于此无法单独生成，需并镜
DEFAULT_MAX_DURATION = 15  # 缺省按 2.0 系列


def resolve_max_duration(model_family):
    """从 model_family 字符串解析单镜时长上限；无法识别时按 2.0 系列 15s。"""
    m = (model_family or "").lower()
    if "2-5" in m or "2.5" in m:
        return MODEL_DURATION_LIMIT["2.5"]
    if "mini" in m:
        return MODEL_DURATION_LIMIT["2.0-mini"]
    if "fast" in m:
        return MODEL_DURATION_LIMIT["2.0-fast"]
    if "2-0" in m or "2.0" in m:
        return MODEL_DURATION_LIMIT["2.0"]
    return DEFAULT_MAX_DURATION


def _norm(v):
    return (v or "").strip()


def consistency_report(spec):
    """程序化落地 SKILL.md 交付前清单，返回 (errors, warnings)。"""
    errors = []
    warnings = []

    chars = spec.get("characters", [])
    shots = spec.get("shots", [])
    char_anchors = {_norm(c.get("anchor_phrase", "")) for c in chars if _norm(c.get("anchor_phrase"))}

    # 1) anchor phrase 逐字一致：每镜 anchor 应与某角色 anchor_phrase 完全相等
    for s in shots:
        a = _norm(s.get("anchor"))
        if not a:
            continue  # 缺 anchor 由 validate() 处理
        if char_anchors and a not in char_anchors:
            warnings.append(
                f"镜 {s.get('shot_id', '?')} 的 anchor 与任何角色 anchor_phrase 都不完全一致"
                f"——近义词/拼写差异会触发 Seedance 视觉重新生成，破坏跨镜一致性。"
            )

    # 2) 单镜时长：不超型号上限、不低于 4s
    max_dur = resolve_max_duration((spec.get("meta") or {}).get("model_family"))
    for s in shots:
        d = s.get("duration_sec")
        if not isinstance(d, (int, float)):
            continue
        if d > max_dur:
            warnings.append(
                f"镜 {s.get('shot_id', '?')} 时长 {d}s 超过当前型号上限 {max_dur}s，"
                f"需切镜或用首尾帧衔接。"
            )
        elif d < MIN_DURATION:
            warnings.append(
                f"镜 {s.get('shot_id', '?')} 时长 {d}s 低于 {MIN_DURATION}s 下限，"
                f"无法单独生成，需并镜。"
            )

    # 3) 单镜头只含一种运动
    for s in shots:
        cam = _norm(s.get("camera")).lower()
        if not cam:
            continue
        kinds = {name for name, pat in MOTION_PATTERNS.items() if re.search(pat, cam)}
        if len(kinds) > 1:
            warnings.append(
                f"镜 {s.get('shot_id', '?')} 镜头语言含多种运动（{cam}）——"
                f"Seedance 单镜建议只承载一种运动。"
            )

    # 4) 关键字段缺失（影响审片与成本）
    for s in shots:
        if not _norm(s.get("audio")):
            warnings.append(f"镜 {s.get('shot_id', '?')} 缺 audio（音效/对白）——音频连续性无法核对。")
        if not _norm(s.get("cost_note")):
            warnings.append(f"镜 {s.get('shot_id', '?')} 缺 cost_note（成本/备注）。")
        if not _norm(s.get("prompt_zh")):
            warnings.append(f"镜 {s.get('shot_id', '?')} 缺 prompt_zh（中文提示词）——纯中文导出时会回退英文。")

    return errors, warnings


def validate(spec):
    errors = []
    meta = spec.get("meta")
    if not isinstance(meta, dict):
        errors.append("meta 字段缺失或不是对象")
    else:
        if "title" not in meta:
            errors.append("meta.title 缺失")

    chars = spec.get("characters", [])
    if not chars:
        errors.append("characters 为空（至少 1 个核心角色）")
    for i, c in enumerate(chars):
        for k in ("id", "name", "anchor_phrase"):
            if k not in c:
                errors.append(f"characters[{i}].{k} 缺失")
        tv = c.get("three_view", {})
        for vk in ("front", "side", "back"):
            if vk not in tv:
                errors.append(f"characters[{i}].three_view.{vk} 缺失")

    shots = spec.get("shots", [])
    if not shots:
        errors.append("shots 为空")
    for i, s in enumerate(shots):
        for k in ("shot_id", "duration_sec", "prompt"):
            if k not in s:
                errors.append(f"shots[{i}].{k} 缺失")
    return errors


def _clean(v):
    return (v or "").replace("\n", " ").strip()


# ---------- 字段中文翻译映射（用于 --pure-zh 纯中文导出，best-effort） ----------
CAMERA_MAP = {
    "Medium shot, slow push-in": "中景，缓慢推近",
    "Tracking alongside, steady": "平行跟拍，稳定",
    "Medium close-up, static": "中近景，固定机位",
    "Wide shot, slow push-in": "远景，缓慢推近",
    "Medium shot, handheld follow": "中景，手持跟随",
    "Close-up, slow push-in": "特写，缓慢推近",
    "Extreme close-up, static": "大特写，固定机位",
    "Wide shot, static": "远景，固定机位",
    "Close-up, static": "特写，固定机位",
    "Medium close-up, slow push-in": "中近景，缓慢推近",
}
LIGHT_MAP = {
    "warm golden morning sunlight, soft shadows": "温暖金色晨光，柔和阴影",
    "bright sunny day, warm daylight": "明亮晴天，温暖日光",
    "soft afternoon light, dappled shade from trees": "柔和午后光，树影斑驳",
    "warm sunlight on water, bright": "水面暖阳，明亮",
    "dappled shade, slightly tense": "斑驳树荫，略带紧张",
    "warm late-afternoon light": "温暖傍晚光",
    "warm golden sunset light, soft": "温暖金色夕阳，柔和",
    "soft warm light, water glints": "柔和暖光，水面微光",
    "bright warm daylight, sparkling water": "明亮温暖日光，波光粼粼",
    "warm golden sunlight, radiant": "温暖金色阳光，明媚",
    "cold blue streetlight, wet reflections": "冷蓝路灯光，湿润反光",
    "dim warm chandelier glow against cool shadow": "幽暗暖色吊灯光映冷影",
    "warm chandelier now dominant, long shadows": "暖色吊灯转为主光，长影",
}
STYLE_MAP = {
    "Pixar-style 3D render, three-quarter lighting, soft ambient occlusion": "Pixar 风格 3D 渲染，四分之三光照，柔和环境光遮蔽",
    "Pixar-style 3D render, three-quarter lighting": "Pixar 风格 3D 渲染，四分之三光照",
    "cinematic, anamorphic flare, film grain": "电影感，变形宽银幕光斑，胶片颗粒",
    "cinematic, shallow depth of field, film grain": "电影感，浅景深，胶片颗粒",
    "cinematic, anamorphic, film grain": "电影感，变形宽银幕，胶片颗粒",
}
QUAL_MAP = {
    "high detail, sharp focus, face clearly visible, facial features stable, no deformation, stable framing, no flicker": "细节清晰、焦点锐利，面部清晰，五官稳定无畸形，画面稳定无闪烁",
    "high detail, sharp focus, body proportions natural, no deformation, stable framing, no flicker": "细节清晰、焦点锐利，身体比例自然，无畸形，画面稳定无闪烁",
    "high detail, sharp focus, facial features stable, no deformation, stable framing, no flicker": "细节清晰、焦点锐利，五官稳定无畸形，画面稳定无闪烁",
    "high detail, sharp focus, stable framing, no flicker, no deformation": "细节清晰、焦点锐利，细节锐利，画面稳定无闪烁无畸形",
}


def _t(v, m):
    return m.get((v or "").strip(), v or "")


def _tv_zh(char):
    """返回角色的中文三视图；缺失时回退英文三视图。"""
    return char.get("three_view_zh") or char.get("three_view", {})


def render_markdown(spec, pure_zh=False):
    meta = spec.get("meta", {})
    chars = spec.get("characters", [])
    shots = spec.get("shots", [])
    L = []

    title = meta.get("title", "Seedance 分镜表")
    L.append(f"# {title}" + ("（纯中文版）" if pure_zh else ""))
    L.append("")
    if pure_zh:
        L.append("> 本表所有可读内容与最终提示词均为中文；人物 anchor phrase 为模型固定身份令牌，保持英文原样以维持跨镜一致性，请勿翻译或改写。")
        L.append("")
    L.append("## 总览")
    L.append("")
    total = meta.get("total_duration_sec") or sum(s.get("duration_sec", 0) for s in shots)
    rows = [
        ("类型", meta.get("genre", "短剧/剧情")),
        ("目标模型", meta.get("model_family", "Seedance 系列")),
        ("画幅", meta.get("aspect_ratio", "9:16")),
        ("分辨率", meta.get("resolution", "720p")),
        ("单镜上限", str(resolve_max_duration(meta.get("model_family"))) + "s"),
        ("总时长", f"{total}s"),
        ("镜头数", str(len(shots))),
    ]
    for k, v in rows:
        L.append(f"- **{k}**：{v}")
    if meta.get("notes"):
        L.append(f"- **备注**：{meta['notes']}")
    L.append("")

    if chars:
        L.append("## 人物三视图定妆参考")
        L.append("")
        L.append("> 定妆图提示词用于 Seedance 文生图/图生图生成角色参考，再作为 I2V 首帧复用，保证跨镜头一致性。")
        L.append("")
        for c in chars:
            L.append(f"### {c['name']}")
            L.append("")
            L.append(f"- **Anchor phrase（逐镜复用）**：{c['anchor_phrase']}")
            if c.get("appearance"):
                L.append(f"- **外观要点**：{c['appearance']}")
            tv = _tv_zh(c) if pure_zh else c.get("three_view", {})
            label_zh = "（中文）" if pure_zh else ""
            for vk, vlabel in (("front", "正面"), ("side", "侧面"), ("back", "背面")):
                L.append("")
                L.append(f"**{vlabel}视图提示词{label_zh}：**")
                L.append("")
                L.append("```")
                L.append(tv.get(vk, ""))
                L.append("```")
            L.append("")

    L.append("## 分镜明细表")
    L.append("")
    L.append("| 镜号 | 时长 | 节拍 | 画面描述 | 镜头语言 | 音效/对白 | 成本/备注 |")
    L.append("| --- | --- | --- | --- | --- | --- | --- |")
    for s in shots:
        cam = _t(s.get("camera"), CAMERA_MAP) if pure_zh else s.get("camera", "")
        L.append(
            f"| {s.get('shot_id', '')} | {s.get('duration_sec', '')}s | {s.get('beat', '')} | "
            f"{_clean(s.get('visual', ''))} | {_clean(cam)} | "
            f"{_clean(s.get('audio', ''))} | {_clean(s.get('cost_note', ''))} |"
        )
    L.append("")

    L.append("## Seedance 提示词清单（" + ("中文，可直接复制" if pure_zh else "英文版 + 中文版，可直接复制") + "）")
    L.append("")
    for s in shots:
        L.append(f"### 镜 {s.get('shot_id', '')} ｜ {s.get('duration_sec', '')}s ｜ {s.get('beat', '')}")
        L.append("")
        parts = []
        if s.get("anchor"):
            parts.append(("主体/Anchor", s["anchor"]))
        if s.get("motion"):
            parts.append(("Motion 运动", s["motion"]))
        if s.get("camera"):
            parts.append(("镜头语言", _t(s.get("camera"), CAMERA_MAP) if pure_zh else s["camera"]))
        if s.get("lighting"):
            parts.append(("光线氛围", _t(s.get("lighting"), LIGHT_MAP) if pure_zh else s["lighting"]))
        if s.get("style"):
            parts.append(("风格", _t(s.get("style"), STYLE_MAP) if pure_zh else s["style"]))
        if s.get("quality"):
            parts.append(("质量/防变形", _t(s.get("quality"), QUAL_MAP) if pure_zh else s["quality"]))
        if s.get("ivf_first_frame"):
            parts.append(("I2V 首帧", s["ivf_first_frame"]))
        for label, val in parts:
            L.append(f"- **{label}**：{val}")
        L.append("")

        if pure_zh:
            zh = s.get("prompt_zh", s.get("prompt", ""))
            if not s.get("prompt_zh"):
                L.append("> ⚠️ 该镜缺 prompt_zh，以下为英文回退：")
            L.append("**完整提示词（中文）：**")
            L.append("")
            L.append("```")
            L.append(zh)
            L.append("```")
            L.append("")
        else:
            L.append("**完整提示词（英文）：**")
            L.append("")
            L.append("```")
            L.append(s.get("prompt", ""))
            L.append("```")
            L.append("")
            zh = s.get("prompt_zh")
            if zh:
                L.append("**完整提示词（中文）：**")
                L.append("")
                L.append("```")
                L.append(zh)
                L.append("```")
                L.append("")

    L.append("## 衔接与一致性说明")
    L.append("")
    L.append("- 一个镜头一条提示词、一种运动；场景切换拆成两个镜头分开生成，不使用提示词内转场标记。")
    L.append("- 衔接分镜将上一镜尾帧作为首帧（I2V），衔接点避免运动模糊/快速形变。")
    L.append("- 同一角色的 anchor phrase 在所有分镜中逐字一致；近义词也会触发视觉重新生成。")
    L.append("- 跨镜衔接处检查是否打断角色对白（音频连续性）。")
    L.append("")

    return "\n".join(L)


def _ensure_openpyxl():
    try:
        import openpyxl  # noqa: F401
        return True
    except ImportError:
        import subprocess
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "openpyxl", "-q"])
            import openpyxl  # noqa: F401
            return True
        except Exception as e:  # noqa: BLE001
            print(f"⚠️  无法加载/安装 openpyxl，跳过 Excel 生成：{e}", file=sys.stderr)
            return False


def build_xlsx(spec, path, pure_zh=False):
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill
    from openpyxl.utils import get_column_letter

    meta = spec.get("meta", {})
    chars = spec.get("characters", [])
    shots = spec.get("shots", [])

    HEADER_FILL = PatternFill("solid", fgColor="2F5496")
    HEADER_FONT = Font(bold=True, color="FFFFFF")
    WRAP = Alignment(horizontal="left", vertical="top", wrap_text=True)
    CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)

    def style_header(cell):
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = CENTER

    wb = Workbook()

    # ---- Sheet 1: 总览 ----
    ws0 = wb.active
    ws0.title = "总览"
    ws0["A1"] = (meta.get("title", "Seedance 分镜表") + ("（纯中文版）" if pure_zh else ""))
    ws0["A1"].font = Font(size=14, bold=True)
    total = meta.get("total_duration_sec") or sum(s.get("duration_sec", 0) for s in shots)
    rows = [
        ("类型", meta.get("genre", "短剧/剧情")),
        ("目标模型", meta.get("model_family", "Seedance 系列")),
        ("画幅", meta.get("aspect_ratio", "9:16")),
        ("分辨率", meta.get("resolution", "720p")),
        ("单镜上限", str(resolve_max_duration(meta.get("model_family"))) + "s"),
        ("总时长", f"{total}s"),
        ("镜头数", str(len(shots))),
        ("备注", meta.get("notes", "")),
    ]
    r = 3
    for k, v in rows:
        kc = ws0.cell(r, 1, k)
        kc.font = Font(bold=True)
        kc.alignment = WRAP
        ws0.cell(r, 2, v).alignment = WRAP
        r += 1
    ws0.column_dimensions["A"].width = 14
    ws0.column_dimensions["B"].width = 70

    # ---- Sheet 2: 人物定妆 ----
    ws1 = wb.create_sheet("人物定妆")
    if pure_zh:
        headers1 = [
            "角色",
            "Anchor phrase（固定身份令牌·英文原样）",
            "外观要点",
            "正面视图提示词(中文)",
            "侧面视图提示词(中文)",
            "背面视图提示词(中文)",
        ]
    else:
        headers1 = [
            "角色",
            "Anchor phrase（逐镜复用）",
            "外观要点",
            "正面视图提示词",
            "侧面视图提示词",
            "背面视图提示词",
        ]
    widths1 = [12, 45, 26, 55, 55, 55]
    for c, h in enumerate(headers1, 1):
        style_header(ws1.cell(1, c, h))
    for i, ch in enumerate(chars, 2):
        tv = _tv_zh(ch) if pure_zh else ch.get("three_view", {})
        vals = [
            ch.get("name", ""),
            ch.get("anchor_phrase", ""),
            ch.get("appearance", ""),
            tv.get("front", ""),
            tv.get("side", ""),
            tv.get("back", ""),
        ]
        for c, v in enumerate(vals, 1):
            cell = ws1.cell(i, c, v)
            cell.alignment = WRAP
    for c, w in enumerate(widths1, 1):
        ws1.column_dimensions[get_column_letter(c)].width = w
    ws1.freeze_panes = "A2"
    ws1.auto_filter.ref = f"A1:{get_column_letter(len(headers1))}{max(2, len(chars)+1)}"

    # ---- Sheet 3: 分镜表 ----
    ws2 = wb.create_sheet("分镜表")
    if pure_zh:
        headers2 = [
            "镜号", "时长", "时间码", "节拍", "画面描述",
            "主体(固定身份令牌·英文)", "Motion 运动", "镜头语言(中)", "光线氛围(中)", "风格(中)",
            "质量/防变形(中)", "Seedance 提示词(中文)", "I2V 首帧", "音效/对白", "成本/备注",
        ]
        widths2 = [6, 6, 12, 8, 32, 30, 32, 18, 20, 18, 26, 50, 26, 26, 30]
    else:
        headers2 = [
            "镜号", "时长", "时间码", "节拍", "画面描述",
            "主体/Anchor", "Motion 运动", "镜头语言", "光线氛围", "风格",
            "质量/防变形", "Seedance 提示词", "Seedance 提示词(中文)", "I2V 首帧", "音效/对白", "成本/备注",
        ]
        widths2 = [6, 6, 12, 8, 32, 30, 32, 18, 20, 18, 26, 50, 50, 26, 26, 30]
    for c, h in enumerate(headers2, 1):
        style_header(ws2.cell(1, c, h))
    for i, s in enumerate(shots, 2):
        if pure_zh:
            zh = s.get("prompt_zh", s.get("prompt", ""))
            vals = [
                s.get("shot_id", ""),
                f"{s.get('duration_sec', '')}s",
                s.get("timecode", ""),
                s.get("beat", ""),
                s.get("visual", ""),
                s.get("anchor", ""),
                s.get("motion", ""),
                _t(s.get("camera"), CAMERA_MAP),
                _t(s.get("lighting"), LIGHT_MAP),
                _t(s.get("style"), STYLE_MAP),
                _t(s.get("quality"), QUAL_MAP),
                zh,
                s.get("ivf_first_frame", ""),
                s.get("audio", ""),
                s.get("cost_note", ""),
            ]
        else:
            vals = [
                s.get("shot_id", ""),
                f"{s.get('duration_sec', '')}s",
                s.get("timecode", ""),
                s.get("beat", ""),
                s.get("visual", ""),
                s.get("anchor", ""),
                s.get("motion", ""),
                s.get("camera", ""),
                s.get("lighting", ""),
                s.get("style", ""),
                s.get("quality", ""),
                s.get("prompt", ""),
                s.get("prompt_zh", ""),
                s.get("ivf_first_frame", ""),
                s.get("audio", ""),
                s.get("cost_note", ""),
            ]
        for c, v in enumerate(vals, 1):
            cell = ws2.cell(i, c, v)
            cell.alignment = WRAP
    for c, w in enumerate(widths2, 1):
        ws2.column_dimensions[get_column_letter(c)].width = w
    ws2.freeze_panes = "A2"
    ws2.auto_filter.ref = f"A1:{get_column_letter(len(headers2))}{max(2, len(shots)+1)}"

    wb.save(path)


def _print_report(enrich_log, errors, warnings):
    if enrich_log.get("prompts_assembled"):
        print(f"🪄  自动拼装提示词：镜 {', '.join(map(str, enrich_log['prompts_assembled']))}")
    if enrich_log.get("three_view_generated"):
        print(f"🪄  自动生成三视图定妆：{', '.join(enrich_log['three_view_generated'])}")
    if errors:
        print(f"\n❌ 硬性错误 {len(errors)} 项：")
        for e in errors:
            print(f"  - {e}")
    if warnings:
        print(f"\n⚠️  自检告警 {len(warnings)} 项（不阻断生成，请核对）：")
        for w in warnings:
            print(f"  - {w}")
    if not errors and not warnings:
        print("✅ 自检通过：anchor 一致性、单镜时长、单镜头运动、关键字段均无问题。")


def main():
    ap = argparse.ArgumentParser(
        description="由 spec JSON 生成 Seedance 分镜表、JSON 与 Excel（支持提示词自动拼装、三视图自动生成、一致性自检、纯中文导出）"
    )
    ap.add_argument("--input", required=True, help="spec JSON 路径")
    ap.add_argument("--out-dir", default=".", help="输出目录")
    ap.add_argument("--no-excel", action="store_true", help="跳过 Excel 生成")
    ap.add_argument("--pure-zh", action="store_true", help="额外产出纯中文版 _纯中文.md / _纯中文.xlsx")
    ap.add_argument("--no-auto", action="store_true", help="关闭 prompt 与 three_view 自动补全，完全按手填输出")
    ap.add_argument("--check", action="store_true", help="仅做校验与自检报告，不写任何文件")
    args = ap.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        spec = json.load(f)

    enrich_log = enrich_spec(spec, auto=not args.no_auto)
    errors = validate(spec)
    cerr, cwarn = consistency_report(spec)

    if args.check:
        _print_report(enrich_log, errors + cerr, cwarn)
        sys.exit(1 if (errors or cerr) else 0)

    if errors:
        print("❌ 校验失败：", file=sys.stderr)
        for e in errors:
            print("  - " + e, file=sys.stderr)
        sys.exit(1)

    _print_report(enrich_log, cerr, cwarn)

    os.makedirs(args.out_dir, exist_ok=True)
    raw_name = spec.get("meta", {}).get("title") or "storyboard"
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in raw_name)
    md_path = os.path.join(args.out_dir, safe + ".md")
    json_path = os.path.join(args.out_dir, safe + ".json")
    xlsx_path = os.path.join(args.out_dir, safe + ".xlsx")
    zh_md_path = os.path.join(args.out_dir, safe + "_纯中文.md")
    zh_xlsx_path = os.path.join(args.out_dir, safe + "_纯中文.xlsx")

    md = render_markdown(spec, pure_zh=False)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 已生成（双语/英文版）：")
    print(f"  Markdown: {md_path}")
    print(f"  JSON:     {json_path}")

    if not args.no_excel:
        if _ensure_openpyxl():
            try:
                build_xlsx(spec, xlsx_path, pure_zh=False)
                print(f"  Excel:    {xlsx_path}")
            except Exception as e:  # noqa: BLE001
                print(f"⚠️  Excel 生成失败：{e}", file=sys.stderr)
        else:
            print("⚠️  已跳过 Excel 生成（缺少 openpyxl）。")

    if args.pure_zh:
        zh_md = render_markdown(spec, pure_zh=True)
        with open(zh_md_path, "w", encoding="utf-8") as f:
            f.write(zh_md)
        print(f"\n✅ 已生成（纯中文版）：")
        print(f"  Markdown: {zh_md_path}")
        if not args.no_excel and _ensure_openpyxl():
            try:
                build_xlsx(spec, zh_xlsx_path, pure_zh=True)
                print(f"  Excel:    {zh_xlsx_path}")
            except Exception as e:  # noqa: BLE001
                print(f"⚠️  纯中文 Excel 生成失败：{e}", file=sys.stderr)


if __name__ == "__main__":
    main()
