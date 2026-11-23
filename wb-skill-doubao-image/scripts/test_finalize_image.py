#!/usr/bin/env python3
"""仅用本仓库 _local 内合成文件与 mock 子进程进行离线回归；产物保留不自动清理。"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

SCRIPT = Path(__file__).with_name("finalize_image.py")
SPEC = importlib.util.spec_from_file_location("finalize_image", SCRIPT)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)
REPO = next(p for p in SCRIPT.parents if (p / ".git").exists())


class FinalizeImageTests(unittest.TestCase):
    def setUp(self):
        root = REPO / "_local"
        root.mkdir(exist_ok=True)
        self.root = Path(tempfile.mkdtemp(prefix="finalize-image-test-", dir=root))
        self.src = self.root / "download.png"
        self.payload = b"synthetic-not-a-real-image"
        self.src.write_bytes(self.payload)
        self.dest = self.root / "result.png"
        self.info = {"format": {"size": "26", "format_name": "png_pipe"}, "streams": [
            {"codec_type": "video", "codec_name": "png", "width": 720, "height": 1280}]}

    def args(self, **changes):
        values = dict(source=str(self.src), dest=str(self.dest), download_complete=True,
                      ffprobe="custom-probe", ffmpeg="custom-decoder",
                      expect_width=None, expect_height=None, min_bytes=None,
                      stability_seconds=0.01, overwrite=False)
        values.update(changes)
        return argparse.Namespace(**values)

    def run_finalize(self, args=None, failure=None):
        def fake_run(command, **kwargs):
            if command[0] == "custom-probe":
                if failure == "bad-json":
                    return subprocess.CompletedProcess(command, 0, "not-json", "")
                info = self.info
                if failure == "no-stream":
                    info = {"format": {}, "streams": []}
                if failure == "no-size":
                    info = {"format": {}, "streams": [
                        {"codec_type": "video", "codec_name": "png"}]}
                return subprocess.CompletedProcess(command, 0, json.dumps(info), "")
            if failure == "decode":
                raise subprocess.CalledProcessError(1, command, stderr="模拟解码错误")
            return subprocess.CompletedProcess(command, 0, "", "")

        run = Mock(side_effect=fake_run)
        isolated = SimpleNamespace(run=run, CalledProcessError=subprocess.CalledProcessError)
        with patch.object(module, "find_tool", side_effect=lambda value: value), \
             patch.object(module.time, "sleep"), \
             patch.object(module, "subprocess", isolated):
            return module.finalize(args or self.args())

    def test_missing_download_declaration(self):
        with self.assertRaisesRegex(ValueError, "下载完成"):
            self.run_finalize(self.args(download_complete=False))

    def test_bad_suffix(self):
        with self.assertRaisesRegex(ValueError, "图片后缀"):
            self.run_finalize(self.args(dest=str(self.root / "result.txt")))

    def test_same_source_and_dest(self):
        with self.assertRaisesRegex(ValueError, "不能与目标相同"):
            self.run_finalize(self.args(dest=str(self.src)))

    def test_existing_dest_rejected(self):
        self.dest.write_bytes(b"keep")
        with self.assertRaises(FileExistsError):
            self.run_finalize()
        self.assertEqual(self.dest.read_bytes(), b"keep")

    def test_overwrite_allowed(self):
        self.dest.write_bytes(b"old")
        result = self.run_finalize(self.args(overwrite=True))
        self.assertTrue(result["ok"])
        self.assertEqual(self.dest.read_bytes(), self.payload)

    def test_empty_source(self):
        self.src.write_bytes(b"")
        with self.assertRaisesRegex(ValueError, "源文件为空"):
            self.run_finalize()

    def test_min_bytes(self):
        with self.assertRaisesRegex(ValueError, "最小字节数"):
            self.run_finalize(self.args(min_bytes=99999))

    def test_source_changed_during_stability(self):
        # 在 finalize 内部第一次 fingerprint 后由 mock 触发变化：用 side_effect 改文件
        original = module.fingerprint
        changed = {"done": False}

        def bump(path):
            result = original(path)
            if not changed["done"]:
                changed["done"] = True
                self.src.write_bytes(self.payload + b"x")
            return result

        with patch.object(module, "fingerprint", side_effect=bump):
            with self.assertRaisesRegex(ValueError, "仍在变化"):
                self.run_finalize()

    def test_bad_probe_json(self):
        with self.assertRaises(json.JSONDecodeError):
            self.run_finalize(failure="bad-json")

    def test_no_image_stream(self):
        with self.assertRaisesRegex(ValueError, "没有有效图像流"):
            self.run_finalize(failure="no-stream")

    def test_missing_dimensions(self):
        with self.assertRaisesRegex(ValueError, "尺寸无效"):
            self.run_finalize(failure="no-size")

    def test_wrong_dimensions(self):
        with self.assertRaisesRegex(ValueError, "宽度不符"):
            self.run_finalize(self.args(expect_width=3840))
        with self.assertRaisesRegex(ValueError, "高度不符"):
            self.run_finalize(self.args(expect_height=2160))

    def test_decode_failure_publishes_nothing(self):
        with self.assertRaises(subprocess.CalledProcessError):
            self.run_finalize(failure="decode")
        self.assertFalse(self.dest.exists())

    def test_success(self):
        result = self.run_finalize(self.args(expect_width=720, expect_height=1280))
        self.assertTrue(result["ok"])
        self.assertEqual(result["width"], 720)
        self.assertEqual(result["height"], 1280)
        self.assertEqual(result["codec"], "png")
        self.assertEqual(self.dest.read_bytes(), self.payload)
        self.assertTrue(self.src.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
