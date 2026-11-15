#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gpt-image-2出图小工具：环境变量取凭据 → curl发请求 → 落盘核对尺寸。

零第三方依赖，Python 3.8+。网络一律交给系统curl：这一层网关按UA拦Python
urllib（403 / error 1010），而且必须绕开系统代理，大响应要直接落文件。

命令：
  auth                      读环境变量并缓存到 ~/.workbuddy/gpt-img-auth.json
  auth --url U --key K      把用户提供的凭据写入缓存
  auth --show               查看当前状态（Key打码）
  generate --prompt "..."    文生图，产物落在调用目录
"""

import argparse
import base64
import json
import os
import re
import struct
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(errors="replace")
        sys.stderr.reconfigure(errors="replace")
    except Exception:
        pass

AUTH_PATH = Path.home() / ".workbuddy" / "gpt-img-auth.json"
ENV_URL = "GPT_IMG_URL"
ENV_KEY = "GPT_IMG_KEY"
MODEL = "gpt-image-2"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
TIMEOUT = 480
DEFAULT_SIZE = "1024x1024"


def out(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def die(msg, code=2):
    print("error: " + msg, file=sys.stderr)
    raise SystemExit(code)


def mask(s):
    if not s:
        return "(未设置)"
    return s[:4] + "..." + s[-4:] if len(s) > 12 else s[:2] + "***"


# ---------------------------------------------------------------- 凭据

def env_value(name):
    """进程环境变量 → Windows用户级 → Windows系统级（直接读注册表）。

    WorkBuddy启动时可能没继承后加的用户级/系统级变量，所以不能只看os.environ。
    """
    v = os.environ.get(name, "").strip()
    if v:
        return v, "process:" + name
    if sys.platform == "win32":
        try:
            import winreg
        except ImportError:
            return "", ""
        for scope, root, path in (
            ("user", winreg.HKEY_CURRENT_USER, "Environment"),
            ("machine", winreg.HKEY_LOCAL_MACHINE,
             r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
        ):
            try:
                with winreg.OpenKey(root, path) as k:
                    value, vtype = winreg.QueryValueEx(k, name)
                if vtype == winreg.REG_EXPAND_SZ:
                    value = winreg.ExpandEnvironmentStrings(value)
                value = str(value).strip()
                if value:
                    return value, scope + ":" + name
            except OSError:
                continue
    return "", ""


def load_auth():
    try:
        data = json.loads(AUTH_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_auth(url, key, url_src, key_src):
    data = {
        "base_url": url,
        "api_key": key,
        "url_source": url_src,
        "key_source": key_src,
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    AUTH_PATH.parent.mkdir(parents=True, exist_ok=True)
    AUTH_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        os.chmod(AUTH_PATH, 0o600)
    except OSError:
        pass
    return data


def normalize_url(u):
    u = u.strip().rstrip("/")
    if not re.match(r"^https?://", u, re.I):
        die("接口地址要是http(s)://开头，当前：" + repr(u))
    # 环境变量只给了域名时补/v1，否则会返回前端HTML且HTTP仍是200
    if urlsplit(u).path in ("", "/"):
        u += "/v1"
    return u


def resolve(cli_url=None, cli_key=None):
    url, usrc = (cli_url.strip(), "cli") if cli_url else env_value(ENV_URL)
    key, ksrc = (cli_key.strip(), "cli") if cli_key else env_value(ENV_KEY)
    cfg = load_auth()
    if not url:
        url, usrc = str(cfg.get("base_url", "")).strip(), "auth"
    if not key:
        key, ksrc = str(cfg.get("api_key", "")).strip(), "auth"
    return url, key, usrc, ksrc


def missing_hint(missing):
    return ("缺" + " / ".join(missing) + "。向用户索要后用 "
            "auth --url <地址> --key <Key> 写入auth文件；不要猜，不要拿别的技能的凭据顶。")


def require_auth(cli_url=None, cli_key=None):
    url, key, usrc, ksrc = resolve(cli_url, cli_key)
    missing = []
    if not url:
        missing.append(ENV_URL)
    if not key:
        missing.append(ENV_KEY)
    if missing:
        out({"ok": False, "missing": missing, "auth_file": str(AUTH_PATH),
             "ask_user": missing_hint(missing)})
        raise SystemExit(3)
    return normalize_url(url), key, usrc, ksrc


def cmd_auth(a):
    if a.show:
        cfg = load_auth()
        url, usrc = env_value(ENV_URL)
        key, ksrc = env_value(ENV_KEY)
        out({
            "auth_file": str(AUTH_PATH),
            "exists": AUTH_PATH.exists(),
            "env_url": {"found": bool(url), "source": usrc, "value": url or ""},
            "env_key": {"found": bool(key), "source": ksrc, "masked": mask(key)},
            "saved_url": cfg.get("base_url", ""),
            "saved_key": mask(cfg.get("api_key", "")),
            "updated_at": cfg.get("updated_at", ""),
        })
        return

    # 显式给值：来自用户，写进auth文件
    if a.url or a.key:
        cfg = load_auth()
        url = (a.url or "").strip() or str(cfg.get("base_url", "")).strip()
        key = (a.key or "").strip() or str(cfg.get("api_key", "")).strip()
        if not url or not key:
            die("要同时有地址和Key才能保存；缺的那项先向用户要")
        url = normalize_url(url)
        save_auth(url, key, "cli", "cli")
        out({"ok": True, "saved_to": str(AUTH_PATH), "base_url": url,
             "api_key": mask(key), "source": "cli"})
        return

    # 无参数：读环境变量，齐了就缓存，缺了报给Agent去问用户
    url, usrc = env_value(ENV_URL)
    key, ksrc = env_value(ENV_KEY)
    if url and key:
        fixed = normalize_url(url)
        save_auth(fixed, key, usrc, ksrc)
        out({"ok": True, "saved_to": str(AUTH_PATH), "base_url": fixed,
             "api_key": mask(key), "url_source": usrc, "key_source": ksrc})
        return
    missing = [n for n, v in ((ENV_URL, url), (ENV_KEY, key)) if not v]
    out({
        "ok": False,
        "missing": missing,
        "auth_file": str(AUTH_PATH),
        "env_url": {"found": bool(url), "source": usrc},
        "env_key": {"found": bool(key), "source": ksrc},
        "ask_user": missing_hint(missing),
    })
    raise SystemExit(3)


# ---------------------------------------------------------------- 网络

def run_curl(extra, out_file, timeout=TIMEOUT):
    """统一走curl：浏览器UA、绕开代理、-o落文件、-w取状态码。"""
    cmd = ["curl", "-sS", "--noproxy", "*", "--max-time", str(timeout),
           "-A", UA, "-o", str(out_file), "-w", "%{http_code}"] + extra
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 30)
    except FileNotFoundError:
        die("找不到curl。Windows 10+ / Git Bash / macOS自带，确认它在PATH里")
    except subprocess.TimeoutExpired:
        die("curl超时（%d秒）。服务端可能已经出图并计费，先查响应文件，不要立刻重试" % timeout)
    if p.returncode != 0:
        die("curl退出码%d：%s" % (p.returncode, (p.stderr or "").strip()[:500]))
    code = (p.stdout or "").strip()[-3:]
    try:
        return int(code)
    except ValueError:
        die("拿不到HTTP状态码：" + repr((p.stdout or "")[:200]))
    return 0


def image_size(path):
    """读PNG/JPEG头拿真实宽高。"""
    raw = Path(path).read_bytes()
    if raw[:8] == b"\x89PNG\r\n\x1a\n" and len(raw) >= 24:
        w, h = struct.unpack(">II", raw[16:24])
        return w, h, "png"
    if raw[:2] == b"\xff\xd8":
        i = 2
        while i < len(raw) - 9:
            if raw[i] != 0xFF:
                i += 1
                continue
            m = raw[i + 1]
            if m in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                     0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                h, w = struct.unpack(">HH", raw[i + 5:i + 9])
                return w, h, "jpeg"
            if m in (0xD8, 0xD9) or 0xD0 <= m <= 0xD7:
                i += 2
                continue
            seg = struct.unpack(">H", raw[i + 2:i + 4])[0]
            i += 2 + seg
    return None


# ---------------------------------------------------------------- 出图

def cmd_generate(a):
    url, key, usrc, ksrc = require_auth(a.url, a.key)
    outdir = Path(a.out_dir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    body = {"model": MODEL, "prompt": a.prompt, "size": a.size, "n": a.n}
    req = outdir / "request.json"
    resp = outdir / "response.json"
    req.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")

    code = run_curl([
        "-X", "POST", url + "/images/generations",
        "-H", "Authorization: Bearer " + key,
        "-H", "Content-Type: application/json",
        "--data-binary", "@" + str(req),
    ], resp)

    report = {
        "http": code, "model": MODEL, "size_requested": a.size, "n": a.n,
        "url_source": usrc, "key_source": ksrc,
        "request_file": str(req), "response_file": str(resp),
    }
    raw = resp.read_bytes() if resp.exists() else b""

    if code != 200:
        report["error_body"] = raw.decode("utf-8", "replace")[:1200]
        out(report)
        raise SystemExit(1)
    if not raw.lstrip().startswith(b"{"):
        report["error_body"] = raw.decode("utf-8", "replace")[:500]
        report["hint"] = "响应不是JSON，多半是接口地址少了/v1或被网关挡了"
        out(report)
        raise SystemExit(1)
    try:
        data = json.loads(raw.decode("utf-8", "replace"))
    except ValueError as e:
        report["error_body"] = "JSON解析失败：" + str(e)
        out(report)
        raise SystemExit(1)
    if isinstance(data, dict) and data.get("error"):
        report["error"] = data["error"]
        out(report)
        raise SystemExit(1)

    items = data.get("data") if isinstance(data, dict) else None
    if not isinstance(items, list) or not items:
        report["hint"] = "响应里没有data[]，把原始响应贴出来核对结构"
        out(report)
        raise SystemExit(1)

    m = re.match(r"^(\d+)x(\d+)$", a.size.strip().lower())
    expect = (int(m.group(1)), int(m.group(2))) if m else None
    files = []
    for idx, item in enumerate(items, 1):
        if not isinstance(item, dict):
            continue
        b64, link = item.get("b64_json"), item.get("url")
        if b64:
            payload = b64.split(",", 1)[-1] if b64.startswith("data:") else b64
            try:
                blob = base64.b64decode(payload)
            except Exception as e:
                files.append({"index": idx, "ok": False, "error": "base64解码失败：" + str(e)})
                continue
        elif link:
            tmp = outdir / ("image-%02d.download" % idx)
            c2 = run_curl(["-L", link], tmp, timeout=180)
            if c2 != 200:
                files.append({"index": idx, "ok": False, "error": "下载图片HTTP %d" % c2})
                continue
            blob = tmp.read_bytes()
            try:
                tmp.unlink()
            except OSError:
                pass
        else:
            files.append({"index": idx, "ok": False, "error": "既没有b64_json也没有url"})
            continue

        if not blob or blob[:1] == b"<" or len(blob) < 1000:
            files.append({"index": idx, "ok": False, "error": "内容不像图片（%d字节）" % len(blob)})
            continue
        ext = "jpg" if blob[:2] == b"\xff\xd8" else "png"
        path = outdir / ("image-%02d.%s" % (idx, ext))
        path.write_bytes(blob)
        entry = {"index": idx, "ok": True, "file": str(path), "bytes": len(blob)}
        sz = image_size(path)
        if sz:
            entry.update({"width": sz[0], "height": sz[1], "format": sz[2]})
            if expect and (sz[0], sz[1]) != expect:
                entry["size_mismatch"] = "请求%dx%d，实际%dx%d" % (expect[0], expect[1], sz[0], sz[1])
        files.append(entry)

    report["images"] = files
    out(report)
    if not any(f.get("ok") for f in files):
        raise SystemExit(1)


# ---------------------------------------------------------------- CLI

def main():
    ap = argparse.ArgumentParser(
        prog="gpt_img.py",
        description="gpt-image-2出图：环境变量取凭据，curl发请求，落盘核对尺寸。",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("auth", help="检查/保存凭据")
    p.add_argument("--url", help="用户提供的接口地址")
    p.add_argument("--key", help="用户提供的API Key")
    p.add_argument("--show", action="store_true", help="查看当前状态，Key打码")
    p.set_defaults(func=cmd_auth)

    p = sub.add_parser("generate", help="文生图")
    p.add_argument("--prompt", required=True, help="画面描述")
    p.add_argument("--size", default=DEFAULT_SIZE, help="宽x高，如1024x1536；auto交给服务端")
    p.add_argument("--n", type=int, default=1, help="张数，默认1")
    p.add_argument("--out-dir", default="gpt-image-2-out", help="产物目录，默认落在调用目录")
    p.add_argument("--url", help="仅本次覆盖接口地址")
    p.add_argument("--key", help="仅本次覆盖Key")
    p.set_defaults(func=cmd_generate)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
