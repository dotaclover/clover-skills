#!/usr/bin/env python3
"""校验并落地豆包网页版下载的视频文件。

用法:
    python finalize_video.py --source "<Downloads/xxx.mp4.crdownload>" \\
        --dest "<workspace>/outputs/片名.mp4" [--expect-duration 10]

做四件事:
1. ffprobe 读取真实容器信息（时长/分辨率/编码/是否有音轨）
2. 校验通过后复制成正式文件名（自动去掉 .crdownload / 加 .mp4）
3. 抽结尾帧存成 <dest>_lastframe.jpg，用于判断是否黑屏
4. 把结果以 JSON 打到 stdout，方便上层直接读

校验失败时退出码为 2，并给出具体原因。
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys

FFPROBE_CANDIDATES = [
    "ffprobe",
    "/c/ffmpeg/bin/ffprobe",
    r"C:\ffmpeg\bin\ffprobe.exe",
    r"C:\ffmpeg\bin\ffprobe",
]
FFMPEG_CANDIDATES = [
    "ffmpeg",
    "/c/ffmpeg/bin/ffmpeg",
    r"C:\ffmpeg\bin\ffmpeg.exe",
    r"C:\ffmpeg\bin\ffmpeg",
]


def find_tool(candidates: list[str]) -> str:
    for cand in candidates:
        found = shutil.which(cand)
        if found:
            return found
        if os.path.isfile(cand):
            return cand
    raise FileNotFoundError(
        "找不到 ffprobe/ffmpeg，请安装 ffmpeg 或把 bin 目录加进 PATH"
    )


def probe(ffprobe: str, path: str) -> dict:
    out = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration,size,format_name",
            "-show_entries",
            "stream=codec_type,codec_name,width,height",
            "-of",
            "json",
            path,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(out.stdout)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, help="下载得到的 .mp4 或 .crdownload 文件")
    ap.add_argument("--dest", required=True, help="落地路径，建议 <workspace>/outputs/名称.mp4")
    ap.add_argument("--expect-duration", type=float, default=None, help="期望时长（秒），误差容忍 1.0s")
    ap.add_argument("--no-frame", action="store_true", help="跳过抽结尾帧")
    args = ap.parse_args()

    src = os.path.abspath(args.source)
    if not os.path.isfile(src):
        print(json.dumps({"ok": False, "error": f"源文件不存在: {src}"}, ensure_ascii=False))
        return 2

    ffprobe = find_tool(FFPROBE_CANDIDATES)
    try:
        info = probe(ffprobe, src)
    except subprocess.CalledProcessError as exc:
        print(
            json.dumps(
                {"ok": False, "error": "ffprobe 解析失败，文件可能还没下完或已损坏",
                 "detail": exc.stderr.strip()},
                ensure_ascii=False,
            )
        )
        return 2

    streams = info.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    duration = float(info.get("format", {}).get("duration", 0) or 0)

    if video is None:
        print(json.dumps({"ok": False, "error": "没有视频流，多半是下载未完成"}, ensure_ascii=False))
        return 2

    if args.expect_duration is not None and abs(duration - args.expect_duration) > 1.0:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": f"时长不符：期望 {args.expect_duration}s，实际 {duration:.2f}s",
                },
                ensure_ascii=False,
            )
        )
        return 2

    dest = os.path.abspath(args.dest)
    if not dest.lower().endswith(".mp4"):
        dest += ".mp4"
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.copy2(src, dest)

    frame_path = None
    if not args.no_frame and duration > 1:
        try:
            ffmpeg = find_tool(FFMPEG_CANDIDATES)
            frame_path = os.path.splitext(dest)[0] + "_lastframe.jpg"
            subprocess.run(
                [
                    ffmpeg, "-v", "error", "-y",
                    "-ss", f"{max(duration - 1.0, 0):.2f}",
                    "-i", dest,
                    "-frames:v", "1",
                    "-vf", "scale=360:-1",
                    frame_path,
                ],
                check=True,
                capture_output=True,
            )
        except Exception:
            frame_path = None

    result = {
        "ok": True,
        "dest": dest,
        "size_bytes": os.path.getsize(dest),
        "duration": round(duration, 2),
        "width": video.get("width"),
        "height": video.get("height"),
        "video_codec": video.get("codec_name"),
        "audio_codec": (audio or {}).get("codec_name"),
        "last_frame": frame_path,
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
