# -*- coding: utf-8 -*-
"""短剧工具共用底座：ffmpeg/ffprobe 调用、实测静音段、PIL 中文叠字原语。

零外部依赖（除 Pillow）。所有脚本从本模块复用，避免每部剧重复造轮子。
约定：中文一律后期用 PIL 叠字，不让生图模型写中文（错字糊字概率太高）。
排版铁律：数字与中文/字母紧挨不加空格；`·` 两侧不留空格；英文词组内部空格保留。
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

# 字体：Windows 微软雅黑。换系统时改这两行。
FONT_BOLD = "C:/Windows/Fonts/msyhbd.ttc"
FONT_REG = "C:/Windows/Fonts/msyh.ttc"

# 静音检测参数（实测有效值）：人声带通避免把风声/车流声当底噪。
NOISE = "-40dB"
MIN_SILENCE = "0.15"
BANDPASS = "highpass=f=250,lowpass=f=3800"
MERGE_GAP = 0.28  # 同一句里的换气间隔 < 0.28s 合并


def ff(args: list[str]) -> None:
    subprocess.run(args, check=True)


def duration(path: Path | str) -> float:
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)], text=True)
    return float(out.strip())


def probe_size(path: Path | str) -> tuple[int, int]:
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0", str(path)],
        text=True).strip().split(",")
    return int(out[0]), int(out[1])


def silences(path: Path | str, noise: str = NOISE, min_sil: str = MIN_SILENCE):
    """返回 [(静音起, 静音止)]。"""
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(path),
         "-af", f"{BANDPASS},silencedetect=noise={noise}:d={min_sil}",
         "-f", "null", "-"], capture_output=True, text=True)
    out = []
    start = None
    for line in proc.stderr.splitlines():
        m = re.search(r"silence_start:\s*([\d.]+)", line)
        if m:
            start = float(m.group(1))
            continue
        m = re.search(r"silence_end:\s*([\d.]+)", line)
        if m and start is not None:
            out.append((start, float(m.group(1))))
            start = None
    return out


def voiced(path: Path | str) -> list[tuple[float, float]]:
    """返回 [(发声起, 发声止)]，已合并句内换气。字幕轴一律以此为准。"""
    dur = duration(path)
    spans, cur, pending = [], 0.0, None
    for s, e in silences(path):
        if s > cur + 0.05:
            spans.append((cur, s))
        pending, cur = s, e
    if pending is None and cur < dur - 0.05:
        spans.append((cur, dur))
    return merge(spans)


def merge(spans: list[tuple[float, float]]) -> list[tuple[float, float]]:
    out: list[tuple[float, float]] = []
    for a, b in spans:
        if out and a - out[-1][1] < MERGE_GAP:
            out[-1] = (out[-1][0], b)
        else:
            out.append((a, b))
    return out


def clean_count(s: str) -> int:
    """计字：去标点只数念出来的字，用于按字数比例拆连读段。"""
    return len(re.sub(r"[，。？！、：；…—\u2014\"“”'‘’（）()\s]", "", s))


def draw_text_run(draw, x, y, parts, stroke=7, anchor="ls"):
    """按 [(文本, font, color)] 逐段绘制，返回整行包围盒 (left, top, right, bottom)。

    逐段用 getbbox(含描边) 量宽再累加，不用 getlength——后者漏算描边与侧边距，
    会让整行偏左。这是「居中必须按包围盒量」这条铁律的实现。
    """
    from PIL import ImageFont  # 局部导入，纯音频脚本无需 Pillow
    cursor, boxes = 0.0, []
    for s, f, _ in parts:
        b = f.getbbox(s, anchor=anchor, stroke_width=stroke)
        boxes.append((cursor + b[0], cursor + b[2], b[1], b[3]))
        cursor += f.getlength(s)
    left = boxes[0][0]
    right = boxes[-1][1]
    top = min(b[2] for b in boxes)
    bottom = max(b[3] for b in boxes)
    xx = x
    for (s, f, color), w in zip(parts, [p[1].getlength(p[0]) for p in parts]):
        draw.text((xx, y), s, font=f, fill=color, anchor=anchor,
                  stroke_width=stroke, stroke_fill=(0, 0, 0))
        xx += w
    return (left, top + y, right, bottom + y)


def centered_x(canvas_w: int, parts, stroke=7, anchor="ls") -> float:
    """算出整行居中后的起始 x。"""
    widths = [f.getlength(s) for s, f, _ in parts]
    boxes = []
    cursor = 0.0
    for (s, f, _), w in zip(parts, widths):
        b = f.getbbox(s, anchor=anchor, stroke_width=stroke)
        boxes.append((cursor + b[0], cursor + b[2]))
        cursor += w
    span = boxes[-1][1] - boxes[0][0]
    return (canvas_w - span) / 2 - boxes[0][0]
