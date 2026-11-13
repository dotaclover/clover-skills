#!/usr/bin/env python3
"""验证已完成下载的视频并安全发布副本；失败返回 JSON 与退出码 2。"""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time


def find_tool(value: str) -> str:
    found = shutil.which(value)
    if found:
        return found
    if Path(value).is_file():
        return str(Path(value).resolve())
    raise FileNotFoundError(f"找不到工具: {value}；请配置路径或加入 PATH")


def probe(ffprobe: str, path: str) -> dict:
    result = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration,size,format_name",
         "-show_entries", "stream=codec_type,codec_name,width,height", "-of", "json", path],
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


def fingerprint(path: Path) -> tuple[int, int]:
    stat = path.stat()
    return stat.st_size, stat.st_mtime_ns


def same_file(left: Path, right: Path) -> bool:
    return left.resolve() == right.resolve() or (right.exists() and os.path.samefile(left, right))


def finalize(args: argparse.Namespace) -> dict:
    src = Path(args.source).resolve()
    dest = Path(args.dest).absolute()
    if dest.suffix.lower() != ".mp4":
        dest = Path(str(dest) + ".mp4")
    frame = dest.with_name(dest.stem + "_lastframe.jpg")
    if not src.is_file():
        raise ValueError(f"源文件不存在: {src}")
    if same_file(src, dest) or same_file(src, frame):
        raise ValueError("源文件不能与目标视频或末帧相同")
    # 即使跳过抽帧，也保护该输出名称对应的已有末帧。
    for target in (dest, frame):
        if target.is_symlink():
            raise ValueError(f"拒绝符号链接目标: {target}")
        if target.exists() and (not args.overwrite or not target.is_file()):
            raise FileExistsError(f"目标已存在，默认拒绝覆盖: {target}")
    if not args.download_complete:
        raise ValueError("须先核浏览器下载完成，再传入 --download-complete")
    if not math.isfinite(args.stability_seconds) or args.stability_seconds <= 0:
        raise ValueError("稳定性观察间隔必须为正数")
    if not math.isfinite(args.duration_tolerance) or args.duration_tolerance < 0:
        raise ValueError("时长容差必须为非负有限值")
    if args.expect_duration is not None and (
        not math.isfinite(args.expect_duration) or args.expect_duration <= 0
    ):
        raise ValueError("期望时长必须为正的有限值")
    before = fingerprint(src)
    if not before[0]:
        raise ValueError("源文件为空")
    time.sleep(args.stability_seconds)
    if fingerprint(src) != before:
        raise ValueError("源文件仍在变化，不能发布")
    ffprobe = find_tool(args.ffprobe)
    ffmpeg = find_tool(args.ffmpeg)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".finalize-", dir=dest.parent) as temp:
        staged = Path(temp) / "video.mp4"
        staged_frame = Path(temp) / "lastframe.jpg"
        shutil.copy2(src, staged)
        if fingerprint(src) != before:
            raise ValueError("复制期间源文件变化，不能发布")
        info = probe(ffprobe, str(staged))
        streams = info.get("streams", [])
        video = next((s for s in streams if s.get("codec_type") == "video"), None)
        audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
        duration = float(info.get("format", {}).get("duration", 0) or 0)
        if video is None or not math.isfinite(duration) or duration <= 0:
            raise ValueError("没有有效视频流或时长")
        if not video.get("width") or not video.get("height"):
            raise ValueError("视频尺寸无效")
        if args.expect_duration is not None and abs(duration - args.expect_duration) > args.duration_tolerance:
            raise ValueError(f"时长不符：期望 {args.expect_duration}s，实际 {duration}s")
        subprocess.run(
            [ffmpeg, "-v", "error", "-xerror", "-nostdin", "-i", str(staged),
             "-map", "0:v:0", "-map", "0:a?", "-f", "null", "-"],
            check=True, capture_output=True, text=True,
        )
        if not args.no_frame:
            subprocess.run(
                [ffmpeg, "-v", "error", "-nostdin", "-n", "-sseof", str(-min(duration, 0.2)),
                 "-i", str(staged), "-frames:v", "1", str(staged_frame)],
                check=True, capture_output=True, text=True,
            )
            if not staged_frame.is_file() or not staged_frame.stat().st_size:
                raise ValueError("末帧抽取失败或为空")
        outputs = [(staged, dest)]
        if not args.no_frame:
            outputs.append((staged_frame, frame))
        created = []
        try:
            for source, target in outputs:
                if args.overwrite:
                    os.replace(source, target)
                else:
                    # 排他创建，避免检查后出现的新文件被覆盖。
                    with target.open("xb") as out:
                        created.append(target)
                        with source.open("rb") as inp:
                            shutil.copyfileobj(inp, out)
        except Exception:
            for target in created:
                target.unlink()
            raise
    return {
        "ok": True, "dest": str(dest), "size_bytes": dest.stat().st_size,
        "duration": round(duration, 3), "width": video.get("width"),
        "height": video.get("height"), "video_codec": video.get("codec_name"),
        "audio_codec": (audio or {}).get("codec_name"),
        "last_frame": None if args.no_frame else str(frame),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", required=True, help="浏览器已确认完成的下载文件")
    ap.add_argument("--dest", required=True, help="目标视频路径")
    ap.add_argument("--download-complete", action="store_true", help="声明已核浏览器下载完成")
    ap.add_argument("--ffprobe", default="ffprobe", help="ffprobe 路径或 PATH 命令名")
    ap.add_argument("--ffmpeg", default="ffmpeg", help="ffmpeg 路径或 PATH 命令名")
    ap.add_argument("--expect-duration", type=float, help="期望时长（秒）")
    ap.add_argument("--duration-tolerance", type=float, default=1.0, help="时长容差（秒，默认 1）")
    ap.add_argument("--stability-seconds", type=float, default=1.0, help="本地文件稳定性观察间隔（秒）")
    ap.add_argument("--no-frame", action="store_true", help="明确跳过末帧抽取")
    ap.add_argument("--overwrite", action="store_true", help="明确授权覆盖视频和末帧；两文件非原子发布，后者失败时前者可能已替换，优先使用新目标路径")
    args = ap.parse_args()
    try:
        result = finalize(args)
    except Exception as exc:
        result = {"ok": False, "error": str(exc)}
        if isinstance(exc, subprocess.CalledProcessError):
            result["detail"] = exc.stderr
        print(json.dumps(result, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
