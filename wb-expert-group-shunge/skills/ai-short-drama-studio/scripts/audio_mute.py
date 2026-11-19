# -*- coding: utf-8 -*-
"""按实测区间把音轨人声压成静音，视频流不动（画面保留）。

适用场景：某句台词要彻底删掉——只删字幕层 PNG 没用，音轨人声还在。
必须音轨单独静音，且字幕层同步删。

关键坑（实测）：
- 静音区间不能压在语音起止点上，要扩到相邻静音缝中央（前后各让 0.3—0.6s），
  否则边界残留 -37/-24dB。
- 用 silencedetect 实测语音边界，再手工取相邻静音缝的中点作为区间端点。
- 验证口径：区间中段 volumedetect 应 -91dB（数字静音）；边界 -38dB 是 AAC
  编码预回声、人耳听不到，别误判为漏音；相邻保留台词应正常（-1.5dB）。

用法：
  # 单文件、区间由参数给出（烧字段内的绝对秒）
  python audio_mute.py in.mp4 out.mp4 15.10:17.90 26.90:30.00
  # 自动：给台词的字数，从实测发声段里定位（辅助，边界仍建议人工核对）
  python audio_mute.py in.mp4 out.mp4 --auto "那你现在看着我，想的是谁？"
"""
from __future__ import annotations

import argparse
from pathlib import Path

from common import clean_count, duration, voiced


def mute_ranges(src: Path, ranges: list[tuple[float, float]], dst: Path,
                vcodec: str = "libx264", acodec: str = "aac") -> None:
    expr = "+".join("between(t,%.3f,%.3f)" % (a, b) for a, b in ranges)
    from common import ff
    ff(["ffmpeg", "-y", "-v", "error", "-i", str(src),
        "-af", "volume=0:enable='%s'" % expr,
        "-map", "0:v", "-map", "0:a",
        "-c:v", vcodec, "-crf", "18", "-preset", "veryfast",
        "-c:a", acodec, "-b:a", "192k",
        "-movflags", "+faststart", str(dst)])
    print("已静音", len(ranges), "段 ->", dst)


def auto_locate(path: Path, target: str) -> tuple[float, float]:
    """按目标字数占比，取最长的若干发声段里匹配的位置（近似，需人工核对）。"""
    spans = voiced(path)
    voice_total = sum(b - a for a, b in spans)
    want = clean_count(target)
    # 无法确定目标在句中哪个位置，最长发声段优先；返回整段供人工细化
    seg = max(spans, key=lambda s: s[1] - s[0])
    print("⚠ 自动定位仅返回最长发声段，请用 silencedetect/抽帧人工核对边界再静音")
    print("  目标字数 %d，全片发声 %.2fs，最长段 %.3f—%.3f" %
          (want, voice_total, seg[0], seg[1]))
    return seg


def verify(path: Path, a: float, b: float) -> None:
    import subprocess
    mid_a, mid_b = a + (b - a) * 0.15, b - (b - a) * 0.15
    out = subprocess.run(
        ["ffmpeg", "-v", "info", "-i", str(path),
         "-af", f"atrim={mid_a}:{mid_b},volumedetect", "-f", "null", "-"],
        capture_output=True, text=True).stderr
    for line in out.splitlines():
        if "mean_volume" in line or "max_volume" in line:
            print("  ", line.strip())


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("ranges", nargs="*", help="区间 a:b（秒），如 15.10:17.90")
    ap.add_argument("--auto", help="按台词自动定位（仅近似，需人工核对）")
    ap.add_argument("--verify", action="store_true", help="静音后测区间中段音量")
    a = ap.parse_args()

    src = Path(a.src)
    if a.auto:
        seg = auto_locate(src, a.auto)
        ranges = [seg]
    else:
        ranges = [(float(x.split(":")[0]), float(x.split(":")[1])) for x in a.ranges]
    if not ranges:
        ap.error("需要给区间 a:b，或用 --auto")
    mute_ranges(src, ranges, Path(a.dst))
    if a.verify:
        for r in ranges:
            print("区间", r)
            verify(Path(a.dst), *r)


if __name__ == "__main__":
    main()
