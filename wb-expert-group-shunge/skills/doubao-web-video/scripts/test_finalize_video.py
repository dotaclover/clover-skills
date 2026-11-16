#!/usr/bin/env python3
"""仅用仓库 _local 内合成文件和 mock 子进程进行离线回归。"""

import argparse
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

SCRIPT = Path(__file__).with_name("finalize_video.py")
SPEC = importlib.util.spec_from_file_location("finalize_video", SCRIPT)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)
REPO = next(p for p in SCRIPT.parents if (p / ".git").exists())


class FinalizeTests(unittest.TestCase):
    def setUp(self):
        root = REPO / "_local"
        root.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="finalize-mock-", dir=root)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.src = self.root / "source.crdownload"
        self.src.write_bytes(b"synthetic-not-a-real-video")
        self.dest = self.root / "result.mp4"
        self.frame = self.root / "result_lastframe.jpg"
        self.info = {"format": {"duration": "2"}, "streams": [
            {"codec_type": "video", "codec_name": "h264", "width": 32, "height": 48}]}

    def args(self, **changes):
        values = dict(source=str(self.src), dest=str(self.dest), download_complete=True,
                      ffprobe="custom-probe", ffmpeg="custom-encoder", expect_duration=2,
                      duration_tolerance=0.1, stability_seconds=0.01, no_frame=False,
                      overwrite=False)
        values.update(changes)
        return argparse.Namespace(**values)

    def run_mock(self, args=None, failure=None):
        def fake_run(command, **kwargs):
            if command[0] == "custom-probe":
                if failure == "probe":
                    return subprocess.CompletedProcess(command, 0, "not-json", "")
                return subprocess.CompletedProcess(command, 0, json.dumps(self.info), "")
            if failure == "decode" or (failure == "frame" and "-frames:v" in command):
                raise subprocess.CalledProcessError(1, command, stderr="模拟媒体错误")
            if "-frames:v" in command and failure != "empty-frame":
                Path(command[-1]).write_bytes(b"synthetic-jpeg")
            return subprocess.CompletedProcess(command, 0, "", "")
        run = Mock(side_effect=fake_run)
        isolated = SimpleNamespace(run=run, CalledProcessError=subprocess.CalledProcessError)
        with patch.object(module, "find_tool", side_effect=lambda value: value), \
             patch.object(module.time, "sleep"), \
             patch.object(module, "subprocess", isolated):
            result = module.finalize(args or self.args())
            return result, run.call_args_list

    def test_help_safe_without_tools_or_files(self):
        before = sorted(self.root.iterdir())
        with patch.object(sys, "argv", [str(SCRIPT), "--help"]), \
             patch.object(module, "find_tool") as tool, \
             patch.object(module.subprocess, "run") as run, \
             contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as exit_code:
                module.main()
        self.assertEqual(exit_code.exception.code, 0)
        tool.assert_not_called()
        run.assert_not_called()
        self.assertEqual(before, sorted(self.root.iterdir()))

    def test_refuse_existing_video_and_frame_unchanged(self):
        for path in (self.dest, self.frame):
            with self.subTest(path=path):
                path.write_bytes(b"keep-me")
                before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.iterdir()}
                with self.assertRaises(FileExistsError):
                    self.run_mock()
                after = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.iterdir()}
                self.assertEqual(before, after)
                path.unlink()

    def test_no_frame_still_protects_existing_frame(self):
        self.frame.write_bytes(b"keep-frame")
        with self.assertRaises(FileExistsError):
            self.run_mock(self.args(no_frame=True))
        self.assertEqual(self.frame.read_bytes(), b"keep-frame")
        self.assertFalse(self.dest.exists())

    def test_same_source_target_rejected_even_with_overwrite(self):
        self.src = self.root / "source.mp4"
        self.src.write_bytes(b"source")
        with self.assertRaises(ValueError):
            self.run_mock(self.args(dest=str(self.src), overwrite=True))
        self.assertEqual(self.src.read_bytes(), b"source")

    def test_unconfirmed_download_rejected(self):
        with self.assertRaises(ValueError):
            self.run_mock(self.args(download_complete=False))
        self.assertFalse(self.dest.exists())

    def test_unstable_source_rejected(self):
        with patch.object(module, "fingerprint", side_effect=[(10, 1), (11, 2)]):
            with self.assertRaises(ValueError):
                self.run_mock()
        self.assertFalse(self.dest.exists())

    def test_success_and_explicit_tool_paths(self):
        result, calls = self.run_mock()
        self.assertTrue(result["ok"])
        self.assertEqual(self.dest.read_bytes(), self.src.read_bytes())
        self.assertTrue(self.frame.exists())
        self.assertEqual([c.args[0][0] for c in calls],
                         ["custom-probe", "custom-encoder", "custom-encoder"])
        self.assertTrue(all("-y" not in c.args[0] for c in calls))

    def test_explicit_overwrite(self):
        self.dest.write_bytes(b"old-video")
        self.frame.write_bytes(b"old-frame")
        result, _ = self.run_mock(self.args(overwrite=True))
        self.assertTrue(result["ok"])
        self.assertEqual(self.dest.read_bytes(), self.src.read_bytes())
        self.assertEqual(self.frame.read_bytes(), b"synthetic-jpeg")

    def test_media_errors_do_not_publish(self):
        for failure in ("probe", "decode", "frame", "empty-frame"):
            with self.subTest(failure=failure):
                with self.assertRaises(Exception):
                    self.run_mock(failure=failure)
                self.assertFalse(self.dest.exists())
                self.assertFalse(self.frame.exists())

    def test_overwrite_media_error_keeps_old_outputs(self):
        self.dest.write_bytes(b"old-video")
        self.frame.write_bytes(b"old-frame")
        with self.assertRaises(subprocess.CalledProcessError):
            self.run_mock(self.args(overwrite=True), failure="frame")
        self.assertEqual(self.dest.read_bytes(), b"old-video")
        self.assertEqual(self.frame.read_bytes(), b"old-frame")

    def test_bad_duration_and_missing_video(self):
        for info in ({"format": {"duration": "nan"}, "streams": self.info["streams"]},
                     {"format": {"duration": "2"}, "streams": []}):
            self.info = info
            with self.assertRaises(ValueError):
                self.run_mock()
            self.assertFalse(self.dest.exists())

    def test_cli_failure_never_reports_complete(self):
        output = io.StringIO()
        with patch.object(sys, "argv", [str(SCRIPT), "--source", str(self.src),
                                        "--dest", str(self.dest)]), \
             patch.object(module, "finalize", side_effect=RuntimeError("模拟失败")), \
             contextlib.redirect_stdout(output):
            code = module.main()
        self.assertEqual(code, 2)
        self.assertFalse(json.loads(output.getvalue())["ok"])
        self.assertNotIn("dest", json.loads(output.getvalue()))


if __name__ == "__main__":
    unittest.main()
