#!/usr/bin/env python3
"""验证已完成下载的图片并安全发布副本；失败返回 JSON 与退出码 2。"""

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

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def find_tool(value: str) -> str:
    found = shutil.which(value)
    if found:
        return found
    if Path(value).is_file():
        return str(Path(value).resolve())
    raise FileNotFoundError(f"找不到工具: {value}；请配置路径或加入 PATH")


def probe(ffprobe: str, path: str) -> dict:
    result = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=size,format_name",
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
    if dest.suffix.lower() not in IMAGE_SUFFIXES:
        raise ValueError("目标文件名须带图片后缀：" + "、".join(sorted(IMAGE_SUFFIXES)))
    if not src.is_file():
        raise ValueError(f"源文件不存在: {src}")
    if same_file(src, dest):
        raise ValueError("源文件不能与目标相同")
    if dest.is_symlink():
        raise ValueError(f"拒绝符号链接目标: {dest}")
    if dest.exists() and (not args.overwrite or not dest.is_file()):
        raise FileExistsError(f"目标已存在，默认拒绝覆盖: {dest}")
    if not args.download_complete:
        raise ValueError("须先核浏览器下载完成，再传入 --download-complete")
    if not math.isfinite(args.stability_seconds) or args.stability_seconds <= 0:
        raise ValueError("稳定性观察间隔必须为正数")
    for name in ("expect_width", "expect_height", "min_bytes"):
        value = getattr(args, name)
        if value is not None and (not isinstance(value, int) or value <= 0):
            raise ValueError(f"{name} 必须为正整数")
    before = fingerprint(src)
    if not before[0]:
        raise ValueError("源文件为空")
    if args.min_bytes and before[0] < args.min_bytes:
        raise ValueError(f"源文件小于最小字节数: {before[0]} < {args.min_bytes}")
    time.sleep(args.stability_seconds)
    if fingerprint(src) != before:
        raise ValueError("源文件仍在变化，不能发布")
    ffprobe = find_tool(args.ffprobe)
    ffmpeg = find_tool(args.ffmpeg)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".finalize-image-", dir=dest.parent) as temp:
        staged = Path(temp) / ("source" + dest.suffix.lower())
        shutil.copy2(src, staged)
        if fingerprint(src) != before:
            raise ValueError("复制期间源文件变化，不能发布")
        info = probe(ffprobe, str(staged))
        streams = info.get("streams", [])
        image = next((s for s in streams if s.get("codec_type") == "video"), None)
        if image is None:
            raise ValueError("没有有效图像流")
        width, height = image.get("width"), image.get("height")
        if not width or not height:
            raise ValueError("图像尺寸无效")
        if args.expect_width and width != args.expect_width:
            raise ValueError(f"宽度不符：期望 {args.expect_width}，实际 {width}")
        if args.expect_height and height != args.expect_height:
            raise ValueError(f"高度不符：期望 {args.expect_height}，实际 {height}")
        subprocess.run(
            [ffmpeg, "-v", "error", "-xerror", "-nostdin", "-i", str(staged),
             "-map", "0:v:0", "-f", "null", "-"],
            check=True, capture_output=True, text=True,
        )
        if args.overwrite:
            os.replace(staged, dest)
        else:
            with dest.open("xb") as out:
                try:
                    with staged.open("rb") as inp:
                        shutil.copyfileobj(inp, out)
                except Exception:
                    out.close()
                    dest.unlink(missing_ok=True)
                    raise
    return {
        "ok": True, "dest": str(dest), "size_bytes": dest.stat().st_size,
        "width": width, "height": height, "codec": image.get("codec_name"),
        "format": info.get("format", {}).get("format_name"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", required=True, help="浏览器已确认完成的下载图片")
    ap.add_argument("--dest", required=True, help="目标图片路径（须带图片后缀）")
    ap.add_argument("--download-complete", action="store_true", help="声明已核浏览器下载完成")
    ap.add_argument("--ffprobe", default="ffprobe", help="ffprobe 路径或 PATH 命令名")
    ap.add_argument("--ffmpeg", default="ffmpeg", help="ffmpeg 路径或 PATH 命令名")
    ap.add_argument("--expect-width", type=int, help="期望宽度（像素）")
    ap.add_argument("--expect-height", type=int, help="期望高度（像素）")
    ap.add_argument("--min-bytes", type=int, help="源文件最小字节数")
    ap.add_argument("--stability-seconds", type=float, default=1.0, help="本地文件稳定性观察间隔（秒）")
    ap.add_argument("--overwrite", action="store_true", help="明确授权覆盖已存在的目标")
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
