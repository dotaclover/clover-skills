"""所有网络均 mock；不读取用户真实凭据。"""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from urllib import error

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/juhe.py"
spec = importlib.util.spec_from_file_location("juhe", SCRIPT)
juhe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(juhe)


class Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.env = patch.dict(os.environ, {}, clear=True)
        self.env.start()
        self.config = patch.object(juhe, "config_dir", return_value=self.directory)
        self.config.start()

    def tearDown(self):
        self.config.stop()
        self.env.stop()
        self.temp.cleanup()

    def test_missing_status_no_network(self):
        with patch.object(juhe, "fetch_models") as fetch:
            self.assertEqual(juhe.status()["source"], "missing")
            fetch.assert_not_called()

    def test_environment_priority(self):
        with patch.dict(os.environ, {"JUHE_API_KEY": "mock-env"}), patch.object(juhe, "read_saved") as saved:
            self.assertEqual(juhe.credential(), ("mock-env", "environment"))
            self.assertNotIn("mock-env", json.dumps(juhe.status()))
            saved.assert_not_called()

    def test_save_load_and_status_no_secret(self):
        juhe.save_key("mock-only-key")
        self.assertEqual(juhe.credential(), ("mock-only-key", "saved"))
        self.assertNotIn("mock-only-key", json.dumps(juhe.status()))
        path = self.directory / "credential.json"
        if os.name == "nt":
            self.assertNotIn("mock-only-key", path.read_text())
            self.assertEqual(json.loads(path.read_text())["format"], "dpapi-user-v1")
        else:
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            path.chmod(0o644)
            with self.assertRaises(juhe.Failure):
                juhe.read_saved()

    def test_corrupt_saved_is_not_missing(self):
        (self.directory / "credential.json").write_text("broken")
        with self.assertRaises(juhe.Failure) as result:
            juhe.status()
        self.assertEqual(result.exception.kind, "storage")

    def test_models_live_default_and_cached(self):
        with patch.object(juhe, "fetch_models", return_value=["qwen-image-3.0"]) as fetch:
            self.assertEqual(juhe.get_models(juhe.DEFAULT_BASE, "mock")[1], "live")
            self.assertEqual(juhe.get_models(juhe.DEFAULT_BASE, "mock", True)[1], "cache")
            juhe.get_models(juhe.DEFAULT_BASE, "mock")
            self.assertEqual(fetch.call_count, 2)
        self.assertNotIn('"mock"', (self.directory / "models-cache.json").read_text())

    def test_cache_scope_expiry_corruption(self):
        with patch.object(juhe, "fetch_models", return_value=[]) as fetch:
            juhe.get_models(juhe.DEFAULT_BASE, "a")
            juhe.get_models(juhe.DEFAULT_BASE, "b", True)
            juhe.get_models("https://mock.invalid", "b", True)
            with patch.object(juhe.time, "time", return_value=time.time() + juhe.TTL + 1):
                juhe.get_models("https://mock.invalid", "b", True)
            (self.directory / "models-cache.json").write_text("bad")
            juhe.get_models("https://mock.invalid", "b", True)
            self.assertEqual(fetch.call_count, 5)

    def test_401_invalidates_but_network_does_not(self):
        with patch.object(juhe, "fetch_models", return_value=[]):
            juhe.get_models(juhe.DEFAULT_BASE, "mock")
        path = self.directory / "models-cache.json"
        with patch.object(juhe, "fetch_models", side_effect=juhe.Failure("network", "网络失败")):
            with self.assertRaises(juhe.Failure):
                juhe.get_models(juhe.DEFAULT_BASE, "mock")
        self.assertTrue(path.exists())
        with patch.object(juhe, "fetch_models", side_effect=juhe.Failure("unauthorized", "401")):
            with self.assertRaises(juhe.Failure):
                juhe.get_models(juhe.DEFAULT_BASE, "mock")
        self.assertFalse(path.exists())

    def test_save_invalidates_cache(self):
        (self.directory / "models-cache.json").write_text("{}")
        juhe.save_key("mock-only")
        self.assertFalse((self.directory / "models-cache.json").exists())

    def test_http_network_classification_and_redaction(self):
        for exc, kind in [(error.HTTPError("url", 401, "mock-secret", {}, None), "unauthorized"),
                          (error.HTTPError("url", 403, "mock-secret", {}, None), "http"),
                          (error.HTTPError("url", 429, "mock-secret", {}, None), "http"),
                          (error.HTTPError("url", 503, "mock-secret", {}, None), "http"),
                          (error.URLError("mock-secret"), "network"), (TimeoutError("mock-secret"), "network")]:
            with self.subTest(kind=kind), patch.object(juhe.request, "build_opener") as opener:
                opener.return_value.open.side_effect = exc
                with self.assertRaises(juhe.Failure) as result:
                    juhe.fetch_models(juhe.DEFAULT_BASE, "mock-secret")
                self.assertEqual(result.exception.kind, kind)
                self.assertNotIn("mock-secret", str(result.exception))

    def test_get_path_header_timeout_and_unknown(self):
        response = io.StringIO('{"data":[{"id":"new-unknown"}]}')
        with patch.object(juhe.request, "build_opener") as opener:
            opener.return_value.open.return_value = response
            ids = juhe.fetch_models(juhe.DEFAULT_BASE, "mock-only")
            req = opener.return_value.open.call_args.args[0]
            self.assertEqual(req.full_url, juhe.DEFAULT_BASE + "/v1/models")
            self.assertEqual(req.get_method(), "GET")
            self.assertEqual(req.get_header("Authorization"), "Bearer mock-only")
            self.assertEqual(opener.return_value.open.call_args.kwargs["timeout"], 30)
            self.assertEqual(juhe.describe(ids[0])["capability_source"], "unknown")

    def test_invalid_response(self):
        for payload in ['not-json', '{}', '{"data":[{}]}', '[]']:
            with patch.object(juhe.request, "build_opener") as opener:
                opener.return_value.open.return_value = io.StringIO(payload)
                with self.assertRaises(juhe.Failure) as result:
                    juhe.fetch_models(juhe.DEFAULT_BASE, "mock-only")
                self.assertEqual(result.exception.kind, "response")

    def test_qwen_aliases_task_intersection(self):
        ids = ["qwen3.8-max", "qwen-image-3.0", "qwen-image-unverified"]
        for alias in ["千问", "通义千问", "qwen", "QWEN"]:
            result = juhe.resolve(ids, alias, "绘图")
            self.assertEqual(result["selected"], "qwen-image-3.0")
        self.assertEqual(juhe.resolve(ids, "qwen", "chat")["selected"], "qwen3.8-max")
        self.assertFalse(juhe.resolve(["qwen3.8-max"], "千问", "绘图")["candidates"])
        result = juhe.resolve(ids, "qwen-image-unverified", "image")
        self.assertEqual(result["unknown"][0]["capability_source"], "unknown")
        self.assertIsNone(result["selected"])

    def test_exact_mismatch_multiple_and_edit_endpoint(self):
        self.assertFalse(juhe.resolve(["qwen3.8-max"], "qwen3.8-max", "image")["candidates"])
        self.assertIsNone(juhe.resolve(["qwen3.8-max", "qwen3.8-flash"], "qwen", "chat")["selected"])
        self.assertEqual(juhe.resolve(["gpt-image-2"], "image2", "改图")["candidates"][0]["endpoint"], "/v1/images/edits")
        mini = juhe.resolve(["doubao-seedance-2-0-mini-260615"], "seedance", "reference-video")["selected"]
        self.assertEqual(mini, "doubao-seedance-2-0-mini-260615")
        self.assertEqual(juhe.describe(mini)["endpoint"], "/api/v3/contents/generations/tasks")

    def test_https_and_no_redirect(self):
        for url in ["http://mock.invalid", "https://a:b@mock.invalid", "https://mock.invalid/v1", "https://mock.invalid?key=bad"]:
            with self.assertRaises(juhe.Failure):
                juhe.base_url(url)
        self.assertIsNone(juhe.NoRedirect().redirect_request(None, None, 302, "", {}, "https://mock.invalid"))

    def test_cli_noninteractive_and_missing_and_no_key_argument(self):
        with patch.object(sys.stdin, "isatty", return_value=False), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(juhe.main(["auth", "set"]), 2)
            self.assertEqual(juhe.main(["models"]), 2)
            with self.assertRaises(SystemExit):
                juhe.main(["auth", "set", "--key", "mock-only"])

    def test_config_refuses_skill_and_repo(self):
        with patch.object(juhe, "config_dir", self.config.temp_original):
            variable = "LOCALAPPDATA" if os.name == "nt" else "XDG_CONFIG_HOME"
            with patch.dict(os.environ, {variable: str(SCRIPT.parents[2])}):
                with self.assertRaises(juhe.Failure):
                    juhe.config_dir()
            (self.directory / ".git").mkdir()
            with patch.dict(os.environ, {variable: str(self.directory)}):
                with self.assertRaises(juhe.Failure):
                    juhe.config_dir()

    def test_cli_hidden_input_unavailable(self):
        with patch.object(sys.stdin, "isatty", return_value=True), patch.object(juhe.getpass, "getpass", side_effect=juhe.getpass.GetPassWarning), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(juhe.main(["auth", "set"]), 2)
        self.assertFalse((self.directory / "credential.json").exists())

    def test_cli_interactive_hidden_save(self):
        with patch.object(sys.stdin, "isatty", return_value=True), patch.object(juhe.getpass, "getpass", return_value="mock-hidden") as prompt, contextlib.redirect_stdout(io.StringIO()) as output, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(juhe.main(["auth", "set"]), 0)
            prompt.assert_called_once()
            self.assertNotIn("mock-hidden", output.getvalue())
        self.assertEqual(juhe.credential()[1], "saved")

    def test_stdin_save_is_persisted_and_not_echoed(self):
        stdin = io.StringIO("mock-stdin-key\n")
        with patch.object(sys, "stdin", stdin), contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(juhe.main(["auth", "set", "--stdin"]), 0)
            self.assertNotIn("mock-stdin-key", output.getvalue())
            self.assertEqual(juhe.credential(), ("mock-stdin-key", "saved"))
            # 第二次读取只报告状态，证明不会再次索要
            self.assertFalse(juhe.status()["ask_user_for_key"])
            self.assertNotIn("mock-stdin-key", json.dumps(juhe.status()))
        if os.name == "nt":
            self.assertNotIn("mock-stdin-key", (self.directory / "credential.json").read_text())

    def test_stdin_rejects_tty_and_empty(self):
        with patch.object(sys.stdin, "isatty", return_value=True):
            with self.assertRaises(juhe.Failure) as result:
                juhe.read_stream_key(sys.stdin)
            self.assertEqual(result.exception.kind, "interaction")
        for stream in (io.StringIO("   \n"), io.StringIO("")):
            with self.assertRaises(juhe.Failure) as result:
                juhe.read_stream_key(stream)
            self.assertEqual(result.exception.kind, "credential")
        with patch.object(sys, "stdin", io.StringIO("bad key with spaces")), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(juhe.main(["auth", "set", "--stdin"]), 2)
        self.assertFalse((self.directory / "credential.json").exists())

    def test_clear_removes_saved_and_asks_again(self):
        juhe.save_key("mock-clear")
        self.assertFalse(juhe.status()["ask_user_for_key"])
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(juhe.main(["auth", "clear"]), 0)
        self.assertEqual(juhe.status()["source"], "missing")
        self.assertTrue(juhe.status()["ask_user_for_key"])
        self.assertFalse((self.directory / "credential.json").exists())

    def test_material_cli_builds_group_and_asset_filters(self):
        output = io.StringIO()
        with patch.dict(os.environ, {"JUHE_API_KEY": "mock-material"}), \
                patch.object(juhe, "request_json", return_value={"code": 0}) as call, \
                contextlib.redirect_stdout(output):
            self.assertEqual(juhe.main(["material", "groups", "create", "--name", "角色素材",
                                        "--description", "参考素材", "--model", "doubao-seedance-2-0"]), 0)
            self.assertEqual(call.call_args.args[2], "POST")
            self.assertEqual(call.call_args.args[3], juhe.MATERIAL_GROUP_PATH)
            self.assertEqual(call.call_args.kwargs["query"], {"model": "doubao-seedance-2-0"})
            self.assertEqual(call.call_args.kwargs["payload"]["GroupType"], "AIGC")

            self.assertEqual(juhe.main(["material", "groups", "list", "--group-type", "AIGC"]), 0)
            self.assertEqual(call.call_args.args[3], juhe.MATERIAL_GROUP_PATH + "/list")
            self.assertEqual(call.call_args.kwargs["payload"]["Filter"], {"GroupType": "AIGC"})

            self.assertEqual(juhe.main(["material", "assets", "list", "--status", "Active"]), 0)
            self.assertEqual(call.call_args.args[3], juhe.MATERIAL_ASSET_PATH + "/list")
            self.assertEqual(call.call_args.kwargs["payload"]["Filter"],
                             {"Statuses": ["Active"]})

            self.assertEqual(juhe.main(["material", "assets", "list", "--group-id", "mock-group"]), 0)
            self.assertEqual(call.call_args.args[3], juhe.MATERIAL_ASSET_PATH + "/list")
            self.assertEqual(call.call_args.kwargs["payload"]["Filter"],
                             {"GroupIds": ["mock-group"]})
        self.assertNotIn("mock-material", output.getvalue())

    def test_material_liveness_cli_uses_session_endpoints(self):
        output = io.StringIO()
        with patch.dict(os.environ, {"JUHE_API_KEY": "mock-material"}), \
                patch.object(juhe, "request_json", return_value={"code": 0}) as call, \
                contextlib.redirect_stdout(output):
            self.assertEqual(juhe.main(["material", "liveness", "create", "--name", "真人认证",
                                        "--description", "本人授权", "--model", "doubao-seedance-2-0"]), 0)
            self.assertEqual(call.call_args.args[2], "POST")
            self.assertEqual(call.call_args.args[3], juhe.MATERIAL_LIVENESS_PATH)
            self.assertEqual(call.call_args.kwargs["payload"],
                             {"Name": "真人认证", "Description": "本人授权"})
            self.assertEqual(call.call_args.kwargs["query"], {"model": "doubao-seedance-2-0"})

            self.assertEqual(juhe.main(["material", "liveness", "get", "--id", "mock-group",
                                        "--model", "doubao-seedance-2-0"]), 0)
            self.assertEqual(call.call_args.args[2], "GET")
            self.assertEqual(call.call_args.args[3], juhe.MATERIAL_LIVENESS_PATH)
            self.assertIsNone(call.call_args.kwargs["payload"])
            self.assertEqual(call.call_args.kwargs["query"],
                             {"id": "mock-group", "model": "doubao-seedance-2-0"})
        self.assertNotIn("mock-material", output.getvalue())

    def test_material_asset_delete_uses_query_id(self):
        output = io.StringIO()
        with patch.dict(os.environ, {"JUHE_API_KEY": "mock-material"}), \
                patch.object(juhe, "request_json", return_value={"code": 0}) as call, \
                contextlib.redirect_stdout(output):
            self.assertEqual(juhe.main(["material", "assets", "delete", "--id", "mock-asset"]), 0)
            self.assertEqual(call.call_args.args[2], "DELETE")
            self.assertEqual(call.call_args.args[3], juhe.MATERIAL_ASSET_PATH)
            self.assertEqual(call.call_args.kwargs["query"], {"id": "mock-asset"})
            self.assertIsNone(call.call_args.kwargs["payload"])
        self.assertNotIn("mock-material", output.getvalue())

    def test_material_group_delete_uses_request_body(self):
        output = io.StringIO()
        with patch.dict(os.environ, {"JUHE_API_KEY": "mock-material"}), \
                patch.object(juhe, "request_json", return_value={"code": 0}) as call, \
                contextlib.redirect_stdout(output):
            self.assertEqual(juhe.main(["material", "groups", "delete", "--id", "mock-group"]), 0)
            self.assertEqual(call.call_args.args[2], "DELETE")
            self.assertEqual(call.call_args.args[3], juhe.MATERIAL_GROUP_PATH)
            self.assertEqual(call.call_args.kwargs["payload"], {"Id": "mock-group"})
            self.assertIsNone(call.call_args.kwargs["query"])
        self.assertNotIn("mock-material", output.getvalue())

    def test_material_request_json_encodes_utf8_and_rejects_redirects(self):
        response = io.BytesIO(b'{"code":0,"message":"ok"}')
        with patch.object(juhe.request, "build_opener") as opener:
            opener.return_value.open.return_value = response
            result = juhe.request_json(
                juhe.DEFAULT_BASE, "mock-key", "POST", juhe.MATERIAL_GROUP_PATH,
                payload={"Name": "角色素材"}, query={"model": "doubao-seedance-2-0"},
            )
            req = opener.return_value.open.call_args.args[0]
            self.assertEqual(result["code"], 0)
            self.assertIn("model=doubao-seedance-2-0", req.full_url)
            self.assertEqual(req.get_method(), "POST")
            self.assertEqual(req.get_header("Authorization"), "Bearer mock-key")
            self.assertEqual(json.loads(req.data.decode("utf-8")), {"Name": "角色素材"})
            self.assertEqual(opener.return_value.open.call_args.kwargs["timeout"], 60)
        self.assertIsNone(juhe.NoRedirect().redirect_request(None, None, 302, "", {}, "https://mock.invalid"))

    def test_missing_status_requests_key(self):
        stdin = io.StringIO("mock-new\n")
        self.assertTrue(juhe.status()["ask_user_for_key"])
        with patch.object(sys, "stdin", stdin), contextlib.redirect_stdout(io.StringIO()):
            juhe.main(["auth", "set", "--stdin"])
        with patch.object(juhe, "fetch_models", return_value=["qwen-image-3.0"]), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(juhe.main(["resolve", "千问", "--task", "绘图"]), 0)


if __name__ == "__main__":
    unittest.main()
