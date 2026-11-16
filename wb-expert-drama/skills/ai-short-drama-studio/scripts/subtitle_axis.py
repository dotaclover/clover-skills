# -*- coding: utf-8 -*-
"""本地字幕轴：ffmpeg silencedetect 拿静音段 → 反推发声区间 → 按字数比例拆句。

零依赖、不联网、秒级。用户定：不再为定轴调用云端 ASR（太慢）。
有两种模式：

1) 只看发声段（不传 --lines）：
   python subtitle_axis.py clip1.mp4 [clip2.mp4 ...]
2) 按逐字稿生成字幕轴（传 --lines，一句一行，或用 --lines-file）：
   python subtitle_axis.py clip.mp4 --lines "第一句台词" "第二句台词"
   python subtitle_axis.py clip.mp4 --lines-file lines.txt
   输出 TSV：起\t止\t字幕文本，可重定向保存。

做法：
- silencedetect 拿发声段，间隔 < 0.28s 的合并（同一句里的换气）。
- 按每句字数比例在「语音时间」上分配累计边界，再映射回真实时间。
- 边界落进静音缝时吸附到发声边界（字幕不会在没人说话时出现）；
  落进发声段内部时保留原值（那是连读，需要在段内切一刀）。
- 每句最短 0.45s。连读段按字数比例拆，逐字稿文本不改。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from common import clean_count, duration, voiced


def axis(path: Path, lines: list[str]) -> list[tuple[str, float, float]]:
    spans = voiced(path)
    dur = duration(path)
    if not spans:
        raise RuntimeError("没有检测到发声段：检查音频是否需要带通/阈值，或该片是否无人声")
    lengths = [max(1, clean_count(s)) for s in lines]
    total = sum(lengths)
    voice_total = sum(b - a for a, b in spans)

    bounds = [sum(lengths[:i]) * voice_total / total for i in range(len(lines) + 1)]
    bounds[-1] = voice_total

    def to_real(t: float) -> float:
        acc = 0.0
        for a, b in spans:
            if t <= acc + (b - a) + 1e-9:
                return a + (t - acc)
            acc += b - a
        return dur

    def snap(t: float, *, start: bool) -> float:
        for a, b in spans:
            if a <= t <= b:
                return t
        if start:
            for a, b in spans:
                if a > t:
                    return a
            return dur
        last = spans[0][0]
        for a, b in spans:
            if b < t:
                last = b
        return last

    out = []
    for i, s in enumerate(lines):
        t0 = snap(to_real(bounds[i]), start=True)
        t1 = snap(to_real(bounds[i + 1]), start=False)
        if t1 - t0 < 0.45:
            t1 = min(t0 + 0.45, dur - 0.02)
        out.append((s, round(t0, 2), round(t1, 2)))
    return out


def report_spans(path: Path) -> None:
    dur = duration(path)
    spans = voiced(path)
    print(f"\n=== {path.name}  时长 {dur:.3f}s  发声段 {len(spans)} 处 ===")
    for i, (a, b) in enumerate(spans, 1):
        print(f"  发声{i:02d}  {a:6.3f} — {b:6.3f}   ({b-a:5.3f}s)")
    print("  注：ASR 起点偏早 0.3—0.5s（把气口算进去），轴取这里的静音边界；")
    print("      连读段按字数比例在段内切分，逐字稿文本不改。")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("clips", nargs="+", help="原片 mp4（可多个）")
    ap.add_argument("--lines", nargs="*", help="逐字稿，一句一个参数")
    ap.add_argument("--lines-file", help="逐字稿文件，一行一句（UTF-8）")
    a = ap.parse_args()

    lines = a.lines or []
    if a.lines_file:
        lines = [x.strip() for x in Path(a.lines_file).read_text(encoding="utf-8").splitlines() if x.strip()]

    for arg in a.clips:
        p = Path(arg)
        if not lines:
            report_spans(p)
            continue
        for text, t0, t1 in axis(p, lines):
            cps = clean_count(text) / max(0.1, t1 - t0)
            flag = "  ⚠语速%.1f字/秒" % cps if cps > 9 or cps < 2.2 else ""
            print(f"{t0:.2f}\t{t1:.2f}\t{text}{flag}")


if __name__ == "__main__":
    main()
