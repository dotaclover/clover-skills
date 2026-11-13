"""离线回归：仅临时目录、虚构凭据和模拟传输。"""
import base64
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("xq", Path(__file__).with_name("xq.py"))
xq = importlib.util.module_from_spec(spec)
spec.loader.exec_module(xq)


class OfflineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.network = patch("urllib.request.OpenerDirector.open", side_effect=AssertionError("禁止网络"))
        self.network.start()
        self.addCleanup(self.network.stop)
        xq.CONFIG = self.root / "account" / "config.json"
        xq.STATE = self.root / "state" / "tasks"
        xq.LEDGER = self.root / "state" / "ledger.jsonl"
        xq.OFFLINE = False
        xq.NO_PROXY = False

    def cli(self, *args):
        with patch("sys.argv", ["xq.py", *args]), contextlib.redirect_stdout(io.StringIO()):
            xq.main()

    def test_config_and_state_isolation(self):
        cfg = self.root / "a" / "config.json"
        state = self.root / "b"
        self.cli("--config", str(cfg), "--state-dir", str(state), "self-test")
        self.assertEqual(xq.CONFIG, cfg.resolve())
        self.assertEqual(xq.STATE, state.resolve() / "tasks")
        self.assertEqual(xq.LEDGER, state.resolve() / "ledger.jsonl")

    def test_offline_never_reads_config_or_sends(self):
        with patch.object(Path, "read_text", side_effect=AssertionError("禁止读取配置")):
            self.cli("self-test")
            self.cli("image", "--prompt", "测试", "--dry-run")
            self.cli("video", "--prompt", "测试", "--dry-run")
            self.cli("quote", "--prompt", "测试", "--dry-run")

    def test_proxy_default_and_opt_out(self):
        with patch("urllib.request.ProxyHandler") as proxy, patch("urllib.request.build_opener"):
            xq.opener()
            proxy.assert_called_once_with()
            proxy.reset_mock()
            xq.NO_PROXY = True
            xq.opener()
            proxy.assert_called_once_with({})

    def test_existing_outputs_preserved(self):
        out = self.root / "result.png"
        out.write_bytes(b"original")
        with self.assertRaises(FileExistsError):
            xq.write_output(out, "new")
        with self.assertRaises(SystemExit):
            xq.download("https://example.invalid/result", out)
        target = self.root / "task-01.png"
        target.write_bytes(b"original")
        with self.assertRaises(FileExistsError):
            xq.collect([{"b64_json": base64.b64encode(b"new").decode()}], self.root,
                       "image", "fake", "task", "https://example.invalid")
        self.assertEqual(out.read_bytes(), b"original")
        self.assertEqual(target.read_bytes(), b"original")

    def test_environment_credential_supported(self):
        with patch.dict("os.environ", {"XINGQIAO_API_KEY": "fake-env-key"}):
            self.assertEqual(xq.api_key({"api_key": "fake-file-key"}), "fake-env-key")

    def test_state_and_cost_no_fixed_conversion(self):
        xq.save_task("image", {"task_id": "demo", "status": "queued"})
        xq.record_cost("image", {"task_id": "demo", "cost_usd": 0.25}, [])
        row = json.loads(xq.LEDGER.read_text(encoding="utf-8"))
        self.assertNotIn("cost_cny", row)
        self.assertTrue((xq.STATE / "image-demo.json").exists())

    def test_redirect_strips_authorization(self):
        req = xq.urllib.request.Request("https://example.invalid/start", headers={"Authorization": "Bearer fake"})
        redirected = xq.SafeRedirect().redirect_request(req, None, 302, "", {}, "https://media.invalid/result")
        self.assertNotIn("Authorization", redirected.headers)

    def test_media_key_only_for_original_provider(self):
        with patch.object(xq, "download") as download:
            xq.collect([{"url": "https://media.invalid/content"}], self.root,
                       "image", "fake", "task", "https://example.invalid")
            self.assertIsNone(download.call_args.kwargs["key"])
            xq.collect([{"url": "/v1/images/1/content"}], self.root,
                       "image", "fake", "task", "https://example.invalid")
            self.assertEqual(download.call_args.kwargs["key"], "fake")

    def test_request_mock_and_no_submission_retry(self):
        response = unittest.mock.MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = b'{"task_id":"fake"}'
        response.status = 202
        response.headers = {}
        with patch.object(xq, "opener") as factory:
            factory.return_value.open.return_value = response
            data, status, _ = xq.request("POST", "https://example.invalid/tasks", key="fake", body={})
            self.assertEqual(data["task_id"], "fake")
            self.assertEqual(status, 202)
            self.assertEqual(factory.return_value.open.call_count, 1)


if __name__ == "__main__":
    unittest.main()
