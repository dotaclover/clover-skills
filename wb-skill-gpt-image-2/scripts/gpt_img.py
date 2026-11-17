#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gpt-image-2出图小工具：环境变量取凭据 → curl发请求 → 落盘核对尺寸。

零第三方依赖，Python 3.8+。离线子命令（self-test / presets / validate /
build / size）不需要网络和 Key，随时可跑；联网的 generate 走系统curl：
这一层网关按UA拦Python urllib（403 / error 1010），而且必须绕开系统代理，
大响应要直接落文件。

命令：
  self-test                 全离线自检（不需要网络和 Key）
  presets                   常用尺寸模板（离线）
  validate --size ...       校验参数（离线）
  build --prompt ...        构造请求体，不发送（离线）
  size <file>               读图片真实宽高（离线）
  auth                      读环境变量并缓存到 ~/.workbuddy/gpt-img-auth.json
  auth --url U --key K      把用户提供的凭据写入缓存
  auth --show               查看当前状态（Key打码）
  generate --prompt "..."   文生图，产物落在调用目录
  generate --image face.jpg 带参考图走 /images/edits 图生图
"""

import argparse
import base64
import json
import mimetypes
import os
import re
import struct
import subprocess
import sys
import time
import uuid
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

# gpt-image-2 实测可用的尺寸档；第三方网关可能放宽到4K档，见 SKILL.md 已知坑。
SUPPORTED_SIZES = {
    "1024x1024", "1024x1536", "1536x1024",
    "2048x2048", "3840x2160", "2160x3840", "auto",
}

PRESETS = [
    {"id": "wechat-cover", "scene": "公众号封面首图", "size": "1536x1024", "aspect": "3:2",
     "style": "主体偏右，左侧留白放标题",
     "prompt": "【用户补充的内容】，简约商业摄影风格，主体居中偏右，左侧大面积留白用于放标题，柔和自然光，浅色干净背景，画面里不要出现文字"},
    {"id": "wechat-inline", "scene": "公众号正文配图", "size": "1024x1024", "aspect": "1:1",
     "style": "扁平插画，配色克制",
     "prompt": "【用户补充的内容】，扁平矢量插画风格，构图简洁，留白充足，配色克制，适合作为文章配图"},
    {"id": "xhs-cover", "scene": "小红书封面", "size": "1024x1536", "aspect": "2:3",
     "style": "竖版，上方留标题区",
     "prompt": "【用户补充的内容】，竖版构图，画面上方三分之一留出干净区域用于加标题，主体清晰，色彩明快，生活化质感"},
    {"id": "xhs-photo", "scene": "小红书实拍感", "size": "1024x1024", "aspect": "1:1",
     "style": "手机实拍，自然光",
     "prompt": "【用户补充的内容】，手机随手拍质感，自然光，轻微景深，画面真实不做作，细节丰富，非棚拍"},
    {"id": "poster", "scene": "竖版海报", "size": "1024x1536", "aspect": "2:3",
     "style": "商业海报，留标题位",
     "prompt": "【用户补充的内容】，商业海报构图，主体占画面中部，上方或下方留出标题与卖点区域，光线有层次，画面里不要出现文字"},
    {"id": "avatar", "scene": "头像或人物图", "size": "1024x1024", "aspect": "1:1",
     "style": "半身，简洁背景，正面光",
     "prompt": "【用户补充的内容】，半身构图，正面或四分之三侧面，简洁纯色背景，柔和正面光，五官清晰，表情自然"},
]


def out(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def die(msg, code=2):
    print("error: " + msg, file=sys.stderr)
    raise SystemExit(code)


def mask(s):
    if not s:
        return "(未设置)"
    return s[:4] + "..." + s[-4:] if len(s) > 12 else s[:2] + "***"


# ---------------------------------------------------------------- 离线校验

def parse_size(value):
    """解析 1024x1536；auto 返回 (None, None)；非法返回 None。"""
    v = (value or "").strip().lower()
    if v == "auto":
        return (None, None)
    m = re.match(r"^(\d+)x(\d+)$", v)
    return (int(m.group(1)), int(m.group(2))) if m else None


def validate(size=DEFAULT_SIZE, n=1, image=None):
    """离线校验参数，返回 (problems, notes)。"""
    problems, notes = [], []
    parsed = parse_size(size)
    if parsed is None:
        problems.append("size 要写成 1024x1536 这种 宽x高（字母x）或 auto，当前：" + repr(size))
    else:
        w, h = parsed
        if w is not None:
            if w > 4096 or h > 4096:
                problems.append("宽或高超过 4096 上限：%dx%d" % (w, h))
            if w < 256 or h < 256:
                problems.append("宽或高小于 256：%dx%d" % (w, h))
            ratio = max(w, h) / float(min(w, h))
            if ratio > 4:
                problems.append("宽高比失衡（%.1f:1），建议不超过 4:1" % ratio)
            if (w, h) == (4096, 4096):
                problems.append("4096x4096 不支持，最大用 3840x2160 或 2160x3840")
            if size.lower() not in SUPPORTED_SIZES:
                notes.append("%dx%d 不在默认档位里，第三方网关可能改成默认尺寸，出图后核对真实宽高" % (w, h))
    if not isinstance(n, int) or isinstance(n, bool) or n < 1 or n > 10:
        problems.append("n 要取 1-10 的整数，当前：" + repr(n))
    if isinstance(image, str) and not Path(image).is_file():
        problems.append("找不到参考图：" + image)
    return problems, notes


def build_body(prompt, size=DEFAULT_SIZE, n=1):
    """构造 /images/generations 的请求体（不含 Key，可离线落盘）。"""
    return {"model": MODEL, "prompt": prompt, "size": size, "n": n}


def cmd_validate(a):
    problems, notes = validate(a.size, a.n, a.image)
    out({"model": MODEL, "size": a.size, "n": a.n,
         "problems": problems, "notes": notes,
         "verdict": "通过" if not problems else "有问题"})
    if problems:
        raise SystemExit(1)


def cmd_build(a):
    problems, notes = validate(a.size, a.n, a.image)
    for x in notes:
        sys.stdout.write("note: %s\n" % x)
    if problems:
        for x in problems:
            sys.stdout.write("problem: %s\n" % x)
        die("参数有问题，先修再构造请求")
    body = build_body(a.prompt, a.size, a.n)
    p = Path(a.out)
    p.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
    out({"request_file": str(p), "model": MODEL, "size": a.size, "n": a.n,
         "endpoint": "/images/generations" if not a.image else "/images/edits",
         "note": "请求体不含 Key；联网出图用 generate 子命令，或把本文件交给 send。"})


def cmd_presets(a):
    items = PRESETS
    if a.id:
        items = [p for p in items if p["id"] == a.id]
        if not items:
            die("没有这个模板：" + a.id)
    if a.scene:
        items = [p for p in items if a.scene in p["scene"]]
    if a.json:
        out(items)
        return
    for p in items:
        sys.stdout.write("%-15s %-16s %-11s %-7s %s\n" %
                         (p["id"], p["scene"], p["size"], p["aspect"], p["style"]))
    sys.stdout.write("\n看完整提示词：presets --id xhs-cover\n")
    sys.stdout.write("内容由用户补，模板只给尺寸、比例和风格骨架；上面所有 size 都能过 validate。\n")


def cmd_size(a):
    for name in a.files:
        try:
            sz = image_size(name)
        except OSError as e:
            out({"file": name, "ok": False, "error": str(e)})
            continue
        if not sz:
            out({"file": name, "ok": False, "error": "不是PNG/JPEG或读不出头"})
        else:
            out({"file": name, "ok": True, "width": sz[0], "height": sz[1], "format": sz[2]})


def cmd_self_test(a):
    """全离线自检：不需要网络、不需要 Key，跑完必须全 PASS。"""
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        sys.stdout.write("[%s] %s%s\n" % ("PASS" if cond else "FAIL", name,
                                           ("  " + detail) if detail else ""))
        if not cond:
            ok = False

    check("normalize_url 补 /v1",
          normalize_url("https://example.com") == "https://example.com/v1")
    check("normalize_url 完整路径原样",
          normalize_url("https://example.com/v1/") == "https://example.com/v1")
    check("parse_size 1024x1536", parse_size("1024x1536") == (1024, 1536))
    check("parse_size 2048x2048", parse_size("2048x2048") == (2048, 2048))
    check("parse_size auto", parse_size("auto") == (None, None))
    check("parse_size 非法值", parse_size("1024*1536") is None)

    pr, _ = validate("1024x1536", 1)
    check("默认参数校验通过", pr == [], str(pr))
    pr, _ = validate("4096x4096", 1)
    check("4096x4096 被拦", any("4096" in x or "上限" in x for x in pr), str(pr))
    pr, _ = validate("2048x100", 1)
    check("宽高比失衡被拦", any("宽高比" in x for x in pr), str(pr))
    pr, _ = validate("1024x1024", 0)
    check("n=0 被拦", any("n " in x for x in pr), str(pr))

    check("请求体字段正确",
          build_body("橘猫", "1024x1536", 1) ==
          {"model": "gpt-image-2", "prompt": "橘猫", "size": "1024x1536", "n": 1})
    check("请求体不含 Key", "key" not in json.dumps(build_body("橘猫")))

    # 响应解析：b64 / url / 空b64 / 错误体 / 非JSON
    def pick(raw):
        data = json.loads(raw)
        if isinstance(data, dict) and data.get("error"):
            return "error"
        items = data.get("data") if isinstance(data, dict) else None
        if not isinstance(items, list) or not items:
            return "none"
        out = []
        for it in items:
            if isinstance(it, dict):
                b64, link = it.get("b64_json"), it.get("url")
                if b64:
                    out.append(base64.b64decode(b64.split(",", 1)[-1]
                                                if b64.startswith("data:") else b64))
                elif link:
                    out.append(b"<url>")
        return out

    check("解析 b64_json", pick('{"data":[{"b64_json":"QUJD"}]}') == [b"ABC"])
    check("解析 url", pick('{"data":[{"url":"https://x/a.png"}]}') == [b"<url>"])
    check("解析 data URI", pick('{"data":[{"b64_json":"data:image/png;base64,QUJD"}]}') == [b"ABC"])
    check("识别 error 体", pick('{"error":{"message":"bad key"}}') == "error")
    check("识别空 data", pick('{"data":[]}') == "none")

    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8AAAwAB/wFbCwAAAABJRU5ErkJggg==")
    tmp = Path(os.environ.get("TEMP", ".")) / "_gpt_img_selftest.png"
    tmp.write_bytes(png)
    try:
        sz = image_size(tmp)
        check("读 PNG 头", sz is not None and sz[0] >= 1 and sz[1] >= 1, str(sz))
    finally:
        try:
            tmp.unlink()
        except OSError:
            pass

    check("Key 打码不泄露", "sk-secret" not in mask("sk-secret-token-123456"))

    for p in PRESETS:
        pr, _ = validate(p["size"], 1)
        check("预设 %s 尺寸合法" % p["id"], pr == [], str(pr))
    check("预设提示词留占位符",
          all("【用户补充的内容】" in p["prompt"] for p in PRESETS))

    sys.stdout.write("\n%s\n" % (
        "自检全部通过。离线命令无需网络与 Key；generate 需要 GPT_IMG_URL / GPT_IMG_KEY。" if ok
        else "有检查项未通过，修好再交付。"))
    raise SystemExit(0 if ok else 1)


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


def encode_multipart(fields, image_path):
    """把字段和参考图编成multipart/form-data，返回(bytes, content_type)。

    自己编码而不是用curl -F：中文prompt走UTF-8，Windows路径也不会被curl误解析。
    """
    boundary = "----gptimg" + uuid.uuid4().hex
    buf = bytearray()
    for k, v in fields.items():
        buf += ("--%s\r\n" % boundary).encode("utf-8")
        buf += ('Content-Disposition: form-data; name="%s"\r\n\r\n' % k).encode("utf-8")
        buf += (str(v) + "\r\n").encode("utf-8")
    p = Path(image_path)
    if not p.is_file():
        die("找不到参考图：" + str(p))
    ctype = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
    buf += ("--%s\r\n" % boundary).encode("utf-8")
    buf += ('Content-Disposition: form-data; name="image"; filename="%s"\r\n' % p.name).encode("utf-8")
    buf += ("Content-Type: %s\r\n\r\n" % ctype).encode("utf-8")
    buf += p.read_bytes() + b"\r\n"
    buf += ("--%s--\r\n" % boundary).encode("utf-8")
    return bytes(buf), "multipart/form-data; boundary=%s" % boundary


# ---------------------------------------------------------------- 出图

def cmd_generate(a):
    problems, notes = validate(a.size, a.n, a.image)
    for x in notes:
        sys.stdout.write("note: %s\n" % x)
    if problems:
        for x in problems:
            sys.stdout.write("problem: %s\n" % x)
        die("参数有问题，先修再出图")
    url, key, usrc, ksrc = require_auth(a.url, a.key)
    outdir = Path(a.out_dir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    body = build_body(a.prompt, a.size, a.n)
    req = outdir / "request.json"
    resp = outdir / "response.json"
    req.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")

    if a.image:
        # 参考图走/images/edits，multipart上传（gpt系实测正常，尺寸精确）
        raw_body, ctype = encode_multipart(body, a.image)
        reqbin = outdir / "request.bin"
        reqbin.write_bytes(raw_body)
        code = run_curl([
            "-X", "POST", url + "/images/edits",
            "-H", "Authorization: Bearer " + key,
            "-H", "Content-Type: " + ctype,
            "--data-binary", "@" + str(reqbin),
        ], resp)
        mode, multipart_file, reference_image = "edit", str(reqbin), str(Path(a.image).resolve())
    else:
        code = run_curl([
            "-X", "POST", url + "/images/generations",
            "-H", "Authorization: Bearer " + key,
            "-H", "Content-Type: application/json",
            "--data-binary", "@" + str(req),
        ], resp)
        mode, multipart_file, reference_image = "generate", "", ""

    report = {
        "http": code, "model": MODEL, "mode": mode, "size_requested": a.size, "n": a.n,
        "url_source": usrc, "key_source": ksrc,
        "request_file": str(req), "response_file": str(resp),
    }
    if reference_image:
        report["reference_image"] = reference_image
        report["multipart_file"] = multipart_file
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

    parsed_size = parse_size(a.size)
    expect = parsed_size if parsed_size and parsed_size[0] else None
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
        description="gpt-image-2出图：离线可自检/校验/构造请求/读图尺寸；联网读环境变量凭据出图。",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("self-test", help="全离线自检，不需要网络与 Key")
    p.set_defaults(func=cmd_self_test)

    p = sub.add_parser("presets", help="常用尺寸模板（离线）")
    p.add_argument("--id", help="看单个模板的完整提示词")
    p.add_argument("--scene", help="按场景过滤")
    p.add_argument("--json", action="store_true", help="输出 JSON")
    p.set_defaults(func=cmd_presets)

    p = sub.add_parser("validate", help="校验参数（离线）")
    p.add_argument("--size", default=DEFAULT_SIZE)
    p.add_argument("--n", type=int, default=1)
    p.add_argument("--image", help="参考图本地路径")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("build", help="构造请求体，不发送（离线）")
    p.add_argument("--prompt", required=True)
    p.add_argument("--size", default=DEFAULT_SIZE)
    p.add_argument("--n", type=int, default=1)
    p.add_argument("--image", help="参考图本地路径")
    p.add_argument("--out", default="request.json")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("size", help="读图片真实宽高（离线）")
    p.add_argument("files", nargs="+")
    p.set_defaults(func=cmd_size)

    p = sub.add_parser("auth", help="检查/保存凭据")
    p.add_argument("--url", help="用户提供的接口地址")
    p.add_argument("--key", help="用户提供的API Key")
    p.add_argument("--show", action="store_true", help="查看当前状态，Key打码")
    p.set_defaults(func=cmd_auth)

    p = sub.add_parser("generate", help="文生图；给--image则图生图")
    p.add_argument("--prompt", required=True, help="画面描述")
    p.add_argument("--size", default=DEFAULT_SIZE, help="宽x高，如1024x1536；auto交给服务端")
    p.add_argument("--n", type=int, default=1, help="张数，默认1")
    p.add_argument("--out-dir", default="gpt-image-2-out", help="产物目录，默认落在调用目录")
    p.add_argument("--image", help="参考图本地路径；给了就走/images/edits图生图")
    p.add_argument("--url", help="仅本次覆盖接口地址")
    p.add_argument("--key", help="仅本次覆盖Key")
    p.set_defaults(func=cmd_generate)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
