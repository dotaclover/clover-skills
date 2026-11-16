"""离线安全回归；随机测试素材与结果仅写入仓库_local，保留产物且不自动删除。"""
import argparse
import contextlib
import importlib.util
import io
import json
import socket
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("pip_builder", HERE / "build_pip_shorts.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class SafetyTests(unittest.TestCase):
    def setUp(self):
        # 保留隔离的随机测试产物供复核，不自动删除或触发宿主删除守卫。
        self.root = Path(tempfile.mkdtemp(prefix="pip-test-", dir=TEST_ROOT))
        self.inputs = self.root / "inputs"
        self.inputs.mkdir()
        (self.inputs / "media").mkdir()
        self.config = json.loads((HERE / "example_config.json").read_text(encoding="utf-8"))
        for name in ("background.mp4", "screen.mp4", "overview.wav", "step-one.wav", "step-two.wav"):
            (self.inputs / "media" / name).write_bytes(b"mock-local-media")
        self.path = self.inputs / "config.json"
        self.save()
        self.out = self.root / "output"
        self.network = patch.object(socket, "socket", side_effect=AssertionError("禁止网络"))
        self.network.start()
        self.addCleanup(self.network.stop)

    def save(self):
        self.path.write_text(json.dumps(self.config, ensure_ascii=False), encoding="utf-8")

    def args(self, *extra):
        return ["--config", str(self.path), "--output-dir", str(self.out), *extra]

    def invoke(self, args):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return builder.main(args)

    def snapshot(self):
        return {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}

    def test_help_has_no_io_or_process(self):
        with patch.object(builder.subprocess, "run", side_effect=AssertionError("禁止子进程")), \
             patch.object(Path, "read_text", side_effect=AssertionError("help禁止读取")), \
             patch.object(Path, "mkdir", side_effect=AssertionError("禁止创建")), \
             patch.object(Path, "write_text", side_effect=AssertionError("禁止写入")):
            with self.assertRaises(SystemExit) as exc:
                self.invoke(["--help"])
            self.assertEqual(exc.exception.code, 0)

    def test_dry_run_and_foreign_config_resolution(self):
        before = self.snapshot()
        with patch.object(builder.subprocess, "run", side_effect=AssertionError("禁止子进程")), \
             patch.object(Path, "mkdir", side_effect=AssertionError("禁止创建")), \
             patch.object(Path, "write_text", side_effect=AssertionError("禁止写入")):
            self.assertEqual(self.invoke(self.args("--dry-run")), 0)
            config, _ = builder.load_config(self.path, self.out)
            self.assertEqual(config["recording"], (self.inputs / "media/screen.mp4").resolve())
        self.assertEqual(before, self.snapshot())
        self.assertFalse(self.out.exists())

    def test_existing_output_and_input_directories_rejected(self):
        self.out.mkdir()
        (self.out / "keep.txt").write_text("保留", encoding="utf-8")
        before = self.snapshot()
        for output in (self.out, self.inputs / "new-output", self.inputs / "media" / "nested", self.path):
            with self.assertRaises(SystemExit) as exc:
                self.invoke(["--config", str(self.path), "--output-dir", str(output), "--dry-run"])
            self.assertEqual(exc.exception.code, 2)
        self.assertEqual(before, self.snapshot())

    def test_invalid_cli_and_remote_source_rejected(self):
        with patch.object(builder.subprocess, "run", side_effect=AssertionError("禁止子进程")):
            for args in ([], ["--unknown"], ["--config"]):
                with self.assertRaises(SystemExit):
                    self.invoke(args)
            self.config["recording"] = "https://invalid.example/media.mp4"
            self.save()
            with self.assertRaises(SystemExit):
                self.invoke(self.args("--dry-run"))
        self.assertFalse(self.out.exists())

    def test_subtitles_only_no_process(self):
        with patch.object(builder.subprocess, "run", side_effect=AssertionError("禁止子进程")):
            self.assertEqual(self.invoke(self.args("--subs-only")), 0)
        text = (self.out / "subtitles.ass").read_text(encoding="utf-8")
        self.assertIn("步骤一", text)
        self.assertIn("Microsoft YaHei", text)
        self.assertFalse((self.out / "video.mp4").exists())

    def test_complete_generation_commands_mocked(self):
        commands = []
        c, _ = builder.load_config(self.path, self.out)
        total = builder.plan(c)["total"]

        def fake_run(args, **kwargs):
            commands.append((args, kwargs))
            if args[0] == "ffprobe":
                name = Path(args[-1]).name
                seconds = total if name == "video.mp4" else 1 if name.endswith(".wav") else 12
                return builder.subprocess.CompletedProcess(args, 0, str(seconds), "")
            dest = Path(args[-1])
            self.assertIn(self.out.resolve(), dest.resolve().parents)
            self.assertIn("-n", args)
            self.assertNotIn("-y", args)
            dest.write_bytes(b"mock-generated-media")
            return builder.subprocess.CompletedProcess(args, 0, "", "")

        before = {p: p.read_bytes() for p in self.inputs.rglob("*") if p.is_file()}
        with patch.object(builder.subprocess, "run", side_effect=fake_run):
            self.assertEqual(self.invoke(self.args()), 0)
        self.assertTrue((self.out / "video.mp4").exists())
        self.assertTrue(any("overlay=" in str(args) for args, _ in commands))
        self.assertTrue(any("amix=" in str(args) for args, _ in commands))
        final = [entry for entry in commands if "subtitles=subtitles.ass" in entry[0]][0]
        self.assertEqual(final[1]["cwd"], self.out.resolve())
        self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_three_chapters_get_two_gaps(self):
        self.config["beats"] = self.config["beats"] * 2
        self.config["timing"].update(target=20, chapters=3)
        self.config["base"][0]["duration"] = 24
        self.save()
        c, _ = builder.load_config(self.path, self.out)
        result = builder.plan(c)
        self.assertEqual(len([s for s in result["slots"] if s[2] is None]), 4)
        self.assertLessEqual(result["total"], 20)

    def test_mismatched_voice_prevents_output_creation(self):
        with patch.object(builder, "probe", return_value=100):
            with self.assertRaises(SystemExit):
                self.invoke(self.args())
        self.assertFalse(self.out.exists())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test-root", required=True, type=Path)
    parsed = parser.parse_args()
    TEST_ROOT = parsed.test_root.resolve()
    if TEST_ROOT.name != "_local" or not (TEST_ROOT.parent / ".git").exists():
        parser.error("测试根目录必须是仓库根目录下的_local")
    TEST_ROOT.mkdir(exist_ok=True)
    unittest.main(argv=[sys.argv[0]], verbosity=2)
