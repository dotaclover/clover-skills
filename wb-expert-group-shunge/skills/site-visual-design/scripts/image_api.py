#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""站点配图工具：同步兼容接口与 rrw 专用异步队列。

端点通过 --base-url 配置；模型与规格以供应商当前文档为准。
默认尊重系统代理；--no-proxy 显式指定直连范围。--config 指定配置文件，
旧技能配置只有 --allow-legacy-config 才读取。输出默认拒绝覆盖。
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
import tempfile
import unicodedata
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(errors="replace")
        sys.stderr.reconfigure(errors="replace")
    except Exception:
        pass

# ---------------------------------------------------------------- 常量

CONFIG_PATH = Path.home() / ".site-visual-design" / "config.json"

# 旧配置仅在用户明确允许时读取，不自动跨技能共享凭据。
LEGACY_CONFIG_PATH = Path.home() / ".aigc-image" / "config.json"
ALLOW_LEGACY_CONFIG = False
OVERWRITE = False
NO_PROXY = None
UA = "site-visual-design/1.0"


def check_output(path):
    if Path(path).exists() and not OVERWRITE:
        die("输出已存在：%s；换新路径或显式 --overwrite" % path)


def network_args():
    return ["--noproxy", NO_PROXY] if NO_PROXY is not None else []

PROVIDERS = {
    "sub": {
        "name": "sub.aicodexvip.top",
        "base_url": "https://sub.aicodexvip.top/v1",
        "proto": "openai",
        "models": ["gpt-image-2", "gpt-image-2.5-flare", "gpt-image-2.5-sunburst"],
        "note": "OpenAI 兼容同步接口，走 curl + 浏览器 UA",
    },
    "rrw": {
        "name": "api.novqiao.com",
        "base_url": "https://api.novqiao.com",
        "proto": "rrw-image-v2",
        "models": [],
        "note": "专用图片队列，异步任务，支持询价与幂等键",
    },
}

# 历史示例尺寸；不是所有兼容服务的强制规格。
GPT_SIZES = {"1024x1024", "1536x1024", "1024x1536", "auto", "512x512", "256x256"}

# 站点配图的尺寸档（配合 plan 用）
SIZE_RULES = [
    (1536, 1024, "首屏大图 3:2，横版够宽，适合放在首屏或区块顶部"),
    (1024, 1024, "方图，产品菜单图、砖块图、案例图"),
    (1024, 1536, "竖图，人像、店铺门头竖构图、手机海报"),
]


# ---------------------------------------------------------------- 基础工具

def die(msg, code=2):
    sys.stderr.write("error: %s\n" % msg)
    raise SystemExit(code)


def out(obj):
    if isinstance(obj, (dict, list)):
        sys.stdout.write(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")
    else:
        sys.stdout.write(str(obj) + "\n")


def dwidth(s):
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in s)


def pad(s, w):
    return s + " " * max(w - dwidth(s), 0)


def load_config():
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def legacy_config():
    """aigc-image 技能的老配置：{"base_url":..., "api_key":...}，只对 sub 这家生效。"""
    try:
        data = json.loads(LEGACY_CONFIG_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_config(cfg):
    check_output(CONFIG_PATH)
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        os.chmod(CONFIG_PATH, 0o600)
    except OSError:
        pass


def mask(key):
    if not key:
        return "(未设置)"
    if len(key) <= 12:
        return key[:2] + "*" * max(len(key) - 2, 0)
    return "%s...%s" % (key[:4], key[-4:])


def provider_ids():
    return list(PROVIDERS.keys())


def resolve(provider, cli_base=None, cli_key=None):
    """返回 (供应商 id, base_url, key)。命令行 > 环境变量 > 配置文件 > 内置默认地址。"""
    if provider not in PROVIDERS:
        die("未知供应商 %r，可用：%s" % (provider, ", ".join(provider_ids())))
    cfg = load_config().get(provider, {}) or {}
    spec = PROVIDERS[provider]
    legacy = legacy_config() if ALLOW_LEGACY_CONFIG else {}

    # 地址优先级：命令行 > 环境变量 > 本技能配置 > aigc-image 老配置 > 内置默认
    base = (cli_base or "").strip().rstrip("/")
    if not base:
        env = os.environ.get("IMAGE_BASE_URL", "").strip()
        base = env.rstrip("/") if env else ""
    if not base and cfg.get("base_url"):
        base = str(cfg["base_url"]).rstrip("/")
    if not base and provider == "sub" and legacy.get("base_url"):
        base = str(legacy["base_url"]).rstrip("/")
    if not base:
        base = spec["base_url"]

    # Key 优先级：命令行 > 环境变量 > 本技能配置 > aigc-image 老配置
    key = (cli_key or "").strip()
    if not key:
        env = os.environ.get("IMAGE_API_KEY", "").strip()
        key = env
    if not key and cfg.get("api_key"):
        key = str(cfg["api_key"]).strip()
    if not key and provider == "sub" and legacy.get("api_key"):
        key = str(legacy["api_key"]).strip()

    return provider, base, key


# ---------------------------------------------------------------- 网络

def curl(args_list, timeout=480, binary_out=None):
    """跑 curl，默认使用系统代理配置。"""
    cmd = ["curl", "-sS"] + network_args() + ["--max-time", str(timeout)] + args_list
    if binary_out:
        cmd += ["-o", binary_out]
    else:
        cmd += ["-o", "-"]
    try:
        done = subprocess.run(cmd, capture_output=True, timeout=timeout + 30)
    except FileNotFoundError:
        die("找不到 curl。Windows 上装个 curl 或用 Git Bash 的 curl。")
    except subprocess.TimeoutExpired:
        return 0, b"", timeout + 30.0, "curl 超时"
    body = done.stdout or b""
    code = 0
    m = re.search(rb"http=([0-9]{3})", done.stderr or b"")
    if m:
        code = int(m.group(1))
    return code, body, 0.0, (done.stderr or b"").decode("utf-8", "replace")


def curl_json(method, url, key, payload=None, headers=None, timeout=480, out_file=None):
    """发 JSON 请求，返回 (http_code, raw_bytes)。"""
    cmd = ["curl", "-sS"] + network_args() + ["--max-time", str(timeout), "-X", method, url,
           "-A", UA]
    if key:
        cmd += ["-H", "Authorization: Bearer %s" % key]
    cmd += ["-H", "Content-Type: application/json"]
    for k, v in (headers or {}).items():
        cmd += ["-H", "%s: %s" % (k, v)]
    if payload is not None:
        cmd += ["--data-binary", "@-"]
    cmd += ["-w", "\n__HTTP__%{http_code}"]
    try:
        done = subprocess.run(cmd, capture_output=True, timeout=timeout + 30,
                              input=json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None)
    except FileNotFoundError:
        die("找不到 curl。")
    except subprocess.TimeoutExpired:
        return 0, b"curl timeout"
    raw = done.stdout or b""
    m = re.search(rb"__HTTP__([0-9]{3})\s*$", raw)
    code = int(m.group(1)) if m else 0
    return code, (raw[:m.start()] if m else raw)


def curl_multipart(url, key, fields, files, timeout=480):
    """multipart 上传（rrw 上传参考图用）。"""
    cmd = ["curl", "-sS"] + network_args() + ["--max-time", str(timeout), "-X", "POST", url,
           "-H", "Authorization: Bearer %s" % key, "-A", UA]
    for k, v in fields.items():
        cmd += ["-F", "%s=%s" % (k, v)]
    for name, path in files.items():
        cmd += ["-F", "%s=@%s" % (name, path)]
    cmd += ["-w", "\n__HTTP__%{http_code}"]
    try:
        done = subprocess.run(cmd, capture_output=True, timeout=timeout + 30)
    except FileNotFoundError:
        die("找不到 curl。")
    except subprocess.TimeoutExpired:
        return 0, b"curl timeout"
    raw = done.stdout or b""
    m = re.search(rb"__HTTP__([0-9]{3})\s*$", raw)
    code = int(m.group(1)) if m else 0
    return code, (raw[:m.start()] if m else raw)


def curl_download(url, out_path, key=None, timeout=300):
    """下载图片。rrw 的签名链接不需要 Bearer，不要附加 Key。"""
    check_output(out_path)
    cmd = ["curl", "-f", "-sS"] + network_args() + ["--max-time", str(timeout), "-L",
           "-A", UA, "-o", str(out_path)]
    if key:
        cmd += ["-H", "Authorization: Bearer %s" % key]
    cmd += [url]
    try:
        done = subprocess.run(cmd, capture_output=True, timeout=timeout + 30)
    except FileNotFoundError:
        die("找不到 curl。")
    except subprocess.TimeoutExpired:
        return False, "curl 超时"
    if done.returncode != 0 or not Path(out_path).is_file():
        return False, (done.stderr or b"").decode("utf-8", "replace")[:300]
    blob = Path(out_path).read_bytes()
    if blob[:1] == b"<":
        return False, "返回的是 HTML 错误页，不是图片"
    if len(blob) < 1000:
        return False, "只有 %d 字节，多半是错误页" % len(blob)
    return True, "%d KB" % (len(blob) // 1024)


# ---------------------------------------------------------------- 参数校验

def parse_size(value):
    """'1024x1536' → (1024, 1536)；auto 或非法 → None。"""
    if not value:
        return None, None
    v = value.strip().lower()
    if v == "auto":
        return None, None
    m = re.match(r"^(\d{1,5})\s*[x×]\s*(\d{1,5})$", v)
    if not m:
        return None, None
    return int(m.group(1)), int(m.group(2))


def validate(provider, model, size, n, prompt, images):
    """返回 (problems, notes)。"""
    problems, notes = [], []
    if not model:
        problems.append("缺 model：模型名从 models 子命令返回的 id 里取，不要凭印象拼")
    if not prompt:
        problems.append("缺 prompt")
    if size:
        w, h = parse_size(size)
        if w is None:
            problems.append("size 解析失败：%r。写法是 1024x1536" % size)
        else:
            if provider == "sub" and size not in GPT_SIZES:
                notes.append("尺寸不在历史示例档位 %s 中；请核对当前模型文档并检查实际尺寸"
                             % sorted(GPT_SIZES - {"auto"}))
    if n is not None:
        if n < 1:
            problems.append("n 必须 >= 1")
        elif n > 4:
            problems.append("一次别超过 4 张，先跑通 1 张")
        elif n > 1:
            notes.append("多图成倍计费，先跑通 n=1")
    if images and provider == "sub":
        problems.append("sub 的 edits 上传未实现，不能用 --image 冒充图生图；请使用供应商支持的编辑工具")
    if images and provider == "rrw":
        notes.append("rrw 图生图要先 upload 上传参考图拿 resource_id，再把 image_reference_ids 传给任务")
    return problems, notes


def build_body(provider, model, prompt, size, n, response_format=None,
               quality=None, image_size=None, aspect_ratio=None,
               output_format=None, image_reference_ids=None, images=None,
               callback_url=None, idempotency_key=None):
    """构造请求体。两个供应商字段不同，这里只放文档里有的字段。"""
    if provider == "sub":
        if images or image_reference_ids:
            die("sub 编辑上传未实现；不能忽略参考图生成")
        body = {"model": model, "prompt": prompt}
        if size:
            body["size"] = size
        if n is not None:
            body["n"] = n
        if response_format:
            body["response_format"] = response_format
        return body

    # rrw /v1/image-v2/tasks
    body = {"model": model, "prompt": prompt}
    if size:
        body["size"] = size
    if n is not None:
        body["n"] = n
    if image_size:
        body["image_size"] = image_size
    if aspect_ratio:
        body["aspect_ratio"] = aspect_ratio
    if quality:
        body["quality"] = quality
    if output_format:
        body["output_format"] = output_format
    if response_format:
        body["response_format"] = response_format
    if image_reference_ids:
        body["image_reference_ids"] = image_reference_ids
    if images:
        body["images"] = images
    if callback_url:
        body["callback_url"] = callback_url
    if idempotency_key:
        body["_idempotency_key"] = idempotency_key
    return body


def to_curl(provider, base, body, key_env="IMAGE_API_KEY"):
    """等价 curl。Key 用环境变量占位，不落明文。"""
    if provider == "sub":
        url = "$IMAGE_BASE_URL/images/generations"
        lines = [
            "curl -sS --max-time 480 -X POST \"%s\" \\" % url,
            "  -H \"Authorization: Bearer $%s\" \\" % key_env,
            "  -H \"Content-Type: application/json\" \\",
            "  -A \"%s\" \\" % UA,
            "  --data-binary '@request.json' \\",
            "  -o - -w 'http=%{http_code} time=%{time_total}s\\n'",
        ]
        return "\n".join(lines)

    url = "$IMAGE_BASE_URL/v1/image-v2/tasks"
    lines = [
        "curl -sS --max-time 480 -X POST \"%s\" \\" % url,
        "  -H \"Authorization: Bearer $%s\" \\" % key_env,
        "  -H \"Content-Type: application/json\" \\",
    ]
    if body.get("_idempotency_key"):
        lines.append("  -H \"Idempotency-Key: %s\" \\" % body["_idempotency_key"])
    lines += [
        "  --data-binary '@request.json' \\",
        "  -o - -w 'http=%{http_code} time=%{time_total}s\\n'",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------- 出图计划

def cmd_plan(args):
    """把「站点配图」拆成一组任务。只给骨架，具体内容由用户填。"""
    scene = args.scene or "通用"
    items = [
        {"role": "首屏大图", "size": "1536x1024", "ratio": "3:2",
         "prompt": "【门店或产品的主体】，横版构图，主体偏左或偏右，柔和自然光，浅景深，"
                   "干净背景，画面里不要出现文字",
         "note": "首屏是最贵的一块地，别让人物占正中"},
        {"role": "菜单/产品图", "size": "1024x1024", "ratio": "1:1",
         "prompt": "【单品名称】，俯拍或45度，浅色干净背景，食物/商品居中，"
                   "真实质感，自然光，不要文字不要logo",
         "note": "一张图只放一样东西，多个产品不要拼在一张里"},
        {"role": "招牌砖块图", "size": "1024x1024", "ratio": "1:1",
         "prompt": "【主营类别】，能代表这类服务的实拍或特写，浅景深，主体清晰",
         "note": "砖块要小尺寸也认得出，别拍太远"},
        {"role": "案例/环境图", "size": "1536x1024", "ratio": "3:2",
         "prompt": "【现场环境或成果】，纪实感，不摆拍，自然光",
         "note": "案例图用于「我们做过什么」，环境图用于「到店什么样」"},
        {"role": "社交分享图 OG", "size": "1024x1024", "ratio": "1:1",
         "prompt": "【品牌主体】，简洁构图，适合裁成小图仍可辨认",
         "note": "OG 图会在聊天软件里缩得很小"},
    ]
    if args.json:
        out(items)
        return
    sys.stdout.write("场景：%s\n\n" % scene)
    sys.stdout.write(pad("用途", 18) + pad("尺寸", 12) + pad("比例", 8) + "提示词骨架\n")
    sys.stdout.write("-" * 78 + "\n")
    for it in items:
        sys.stdout.write(pad(it["role"], 18) + pad(it["size"], 12) + pad(it["ratio"], 8) + it["prompt"] + "\n")
    sys.stdout.write("\n写死的一句：全站配图风格要一致，把「光线、色温、材质」抄三遍到每条提示词里。\n")
    sys.stdout.write("中文一律不要让模型写，出图后用 overlay 子命令叠字。\n")


# ---------------------------------------------------------------- 子命令

def cmd_providers(args):
    cfg = load_config()
    rows = []
    for pid in provider_ids():
        spec = PROVIDERS[pid]
        c = cfg.get(pid, {}) or {}
        _, base, key = resolve(pid)
        rows.append({
            "id": pid,
            "name": spec["name"],
            "base_url": base,
            "api_key": mask(key),
            "key_source": ("本技能配置" if c.get("api_key")
                           else "aigc-image 老配置" if key and pid == "sub"
                           else "环境变量" if key else "未设置"),
            "models": spec["models"] or "(用 models 子命令查)",
            "note": spec["note"],
        })
    out(rows)


def cmd_init(args):
    cfg = load_config()
    pid = args.provider
    if pid not in PROVIDERS:
        die("未知供应商 %r，可用：%s" % (pid, ", ".join(provider_ids())))
    spec = PROVIDERS[pid]
    base = (args.base_url or "").strip().rstrip("/")
    key = (args.key or "").strip()

    if not base or not key:
        if not sys.stdin.isatty():
            die("非交互环境，请用参数指定：init --provider %s --base-url <URL> --key <KEY>" % pid)
        sys.stdout.write("配置供应商 %s（%s）\n\n" % (pid, spec["name"]))
        if not base:
            sys.stdout.write("接口地址（回车用默认 %s）：" % spec["base_url"])
            line = sys.stdin.readline().strip()
            base = line.rstrip("/") if line else spec["base_url"]
        if not key:
            sys.stdout.write("API Key（回车保留原值）：")
            line = sys.stdin.readline().strip()
            key = line if line else (cfg.get(pid, {}) or {}).get("api_key", "")

    if not key:
        die("Key 不能为空")

    cfg[pid] = {"base_url": base, "api_key": key, "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")}
    save_config(cfg)
    out({"provider": pid, "base_url": base, "api_key": mask(key), "saved_to": str(CONFIG_PATH)})
    sys.stdout.write("\n明文文件，别提交到 Git。下次 models/send 不用再传。\n")


def cmd_models(args):
    provider, base, key = resolve(args.provider, args.base_url, args.key)
    if not key:
        die("缺 Key：用 --key 传入，或先跑 init --provider %s" % provider)

    if provider == "sub":
        code, body = curl_json("GET", base.rstrip("/") + "/models", key, timeout=60)
    else:
        code, body = curl_json("GET", base.rstrip("/") + "/v1/image-v2/models", key, timeout=60)

    sys.stdout.write("http=%d provider=%s\n" % (code, provider))
    if code != 200:
        sys.stdout.write(body.decode("utf-8", "replace")[:1200] + "\n")
        raise SystemExit(1)
    try:
        data = json.loads(body.decode("utf-8", "replace"))
    except ValueError:
        sys.stdout.write("不是 JSON：%s\n" % body.decode("utf-8", "replace")[:400])
        raise SystemExit(1)

    if provider == "sub":
        ids = [m.get("id") for m in data.get("data", []) if isinstance(m, dict)]
        kw = ("image", "dall", "flux", "imagen", "seedream", "kolors", "canvas", "draw")
        out({"total": len(ids),
             "image_like": [i for i in ids if i and any(k in i.lower() for k in kw)],
             "all": ids})
    else:
        out({"models": data.get("data", data)})


def cmd_quote(args):
    provider, base, key = resolve(args.provider, args.base_url, args.key)
    if provider != "rrw":
        die("quote 只有 rrw 这家有。sub 这家直接出图就行。")
    if not key:
        die("缺 Key")
    body = build_body("rrw", args.model, args.prompt or "一只白色陶瓷杯",
                       args.size, args.n, quality=args.quality,
                       image_size=args.image_size, aspect_ratio=args.aspect_ratio)
    body.pop("_idempotency_key", None)
    code, raw = curl_json("POST", base.rstrip("/") + "/v1/image-v2/quote", key, body, timeout=120)
    sys.stdout.write("http=%d\n" % code)
    try:
        sys.stdout.write(json.dumps(json.loads(raw.decode("utf-8", "replace")), ensure_ascii=False, indent=2) + "\n")
    except ValueError:
        sys.stdout.write(raw.decode("utf-8", "replace")[:1200] + "\n")
    raise SystemExit(0 if code == 200 else 1)


def cmd_build(args):
    provider, base, key = resolve(args.provider, args.base_url, args.key)
    problems, notes = validate(provider, args.model, args.size, args.n, args.prompt, args.image)
    for x in notes:
        sys.stdout.write("note: %s\n" % x)
    if problems:
        for x in problems:
            sys.stdout.write("problem: %s\n" % x)
        die("参数有问题，先修再构造请求")
    body = build_body(provider, args.model, args.prompt, args.size, args.n,
                       response_format=args.response_format, quality=args.quality,
                       image_size=args.image_size, aspect_ratio=args.aspect_ratio,
                       output_format=args.output_format,
                       image_reference_ids=args.image_reference_id,
                       images=args.image, callback_url=args.callback_url,
                       idempotency_key=args.idempotency_key)
    Path(args.out).write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
    sys.stdout.write("请求体已写 %s\n\n等价 curl（Key 用环境变量）：\n%s\n" % (args.out, to_curl(provider, base, body)))


def cmd_send(args):
    provider, base, key = resolve(args.provider, args.base_url, args.key)
    if not key:
        die("缺 Key：用 --key 传入，或先跑 init --provider %s" % provider)

    if args.request:
        body = json.loads(Path(args.request).read_text(encoding="utf-8"))
    else:
        problems, notes = validate(provider, args.model, args.size, args.n, args.prompt, args.image)
        for x in notes:
            sys.stdout.write("note: %s\n" % x)
        if problems:
            for x in problems:
                sys.stdout.write("problem: %s\n" % x)
            die("参数有问题")
        body = build_body(provider, args.model, args.prompt, args.size, args.n,
                           response_format=args.response_format, quality=args.quality,
                           image_size=args.image_size, aspect_ratio=args.aspect_ratio,
                           output_format=args.output_format,
                           image_reference_ids=args.image_reference_id,
                           images=args.image, callback_url=args.callback_url,
                           idempotency_key=args.idempotency_key)

    headers = {}
    if args.idempotency_key:
        headers["Idempotency-Key"] = args.idempotency_key

    if provider == "sub":
        url = base.rstrip("/") + "/images/generations"
    else:
        url = base.rstrip("/") + "/v1/image-v2/tasks"
        if args.idempotency_key:
            body.pop("_idempotency_key", None)

    t0 = time.time()
    code, raw = curl_json("POST", url, key, body, headers=headers, timeout=args.timeout)
    secs = time.time() - t0
    sys.stdout.write("http=%d time=%.1fs bytes=%d provider=%s\n" % (code, secs, len(raw), provider))
    if args.out:
        Path(args.out).write_bytes(raw)
        sys.stdout.write("原始响应已存 %s\n" % args.out)
    else:
        sys.stdout.write(raw.decode("utf-8", "replace")[:2000] + "\n")

    if provider == "rrw" and code in (200, 202):
        try:
            data = json.loads(raw.decode("utf-8", "replace"))
        except ValueError:
            data = {}
        if data.get("task_id"):
            sys.stdout.write("\ntask_id=%s status=%s\n" % (data.get("task_id"), data.get("status")))
            sys.stdout.write("接着跑：poll --provider rrw --task-id %s\n" % data.get("task_id"))
    raise SystemExit(0 if code in (200, 202) else 1)


def cmd_poll(args):
    provider, base, key = resolve(args.provider, args.base_url, args.key)
    if provider != "rrw":
        die("poll 只有 rrw 这家需要。sub 是同步接口，出图即返回。")
    if not key:
        die("缺 Key")
    url = base.rstrip("/") + "/v1/image-v2/tasks/%s" % args.task_id
    deadline = time.time() + args.max_wait
    waited = 0
    while True:
        code, raw = curl_json("GET", url, key, timeout=60)
        if code != 200:
            sys.stdout.write("http=%d\n%s\n" % (code, raw.decode("utf-8", "replace")[:800]))
            raise SystemExit(1)
        try:
            data = json.loads(raw.decode("utf-8", "replace"))
        except ValueError:
            sys.stdout.write("响应不是 JSON：%s\n" % raw.decode("utf-8", "replace")[:400])
            raise SystemExit(1)
        status = data.get("status")
        state = data.get("state")
        terminal = bool(data.get("terminal"))
        sys.stdout.write("status=%s state=%s terminal=%s cost_usd=%s\n"
                         % (status, state, terminal, data.get("cost_usd")))
        if terminal or status in ("succeeded", "failed", "canceled"):
            if status == "succeeded":
                for item in (data.get("data") or []):
                    img_url = item.get("url")
                    if img_url:
                        out_dir = Path(args.out_dir)
                        out_dir.mkdir(parents=True, exist_ok=True)
                        target = out_dir / ("rrw-%s.png" % item.get("resource_id", "img"))
                        ok, info = curl_download(img_url, target)
                        sys.stdout.write("下载 %s：%s\n" % (target, info))
                if args.out:
                    Path(args.out).write_bytes(raw)
            else:
                sys.stdout.write("失败：%s\n" % json.dumps(data.get("error", {}), ensure_ascii=False))
            raise SystemExit(0 if status == "succeeded" else 1)
        wait = int(data.get("retry_after_seconds") or 5)
        if time.time() + wait > deadline:
            sys.stdout.write("等了 %d 秒还没到终态，用同一个 task_id 接着查，不要重新提交（会重复计费）。\n" % waited)
            raise SystemExit(2)
        time.sleep(min(wait, 30))
        waited += wait


def cmd_upload(args):
    """rrw 上传参考图，拿 resource_id。"""
    provider, base, key = resolve(args.provider, args.base_url, args.key)
    if provider != "rrw":
        die("upload 只有 rrw 这家有。sub 直接把图放本地或公网地址传进请求体。")
    if not key:
        die("缺 Key")
    path = Path(args.file)
    if not path.is_file():
        die("找不到文件：%s" % path)
    if path.stat().st_size > 25 * 1024 * 1024:
        die("单文件上限 25 MiB，当前 %d MB" % (path.stat().st_size // 1024 // 1024))
    code, raw = curl_multipart(base.rstrip("/") + "/v1/image-v2/references", key, {}, {"file": str(path)})
    sys.stdout.write("http=%d\n" % code)
    sys.stdout.write(raw.decode("utf-8", "replace")[:1000] + "\n")
    raise SystemExit(0 if code == 201 else 1)


# ---------------------------------------------------------------- 解析与落盘

def image_size(path):
    """读 PNG / JPEG 头取真实宽高，返回 (w, h, fmt)；不是图片返回 None。"""
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
            marker = raw[i + 1]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                h, w = struct.unpack(">HH", raw[i + 5:i + 9])
                return w, h, "jpeg"
            if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
                i += 2
                continue
            seg = struct.unpack(">H", raw[i + 2:i + 4])[0]
            i += 2 + seg
    return None


def iter_images(obj):
    """从响应里找图片。兼容 sub 的 data[].b64_json / data[].url 与 rrw 的 data[]。"""
    found = []
    if isinstance(obj, dict):
        if isinstance(obj.get("data"), list):
            for item in obj["data"]:
                if isinstance(item, dict):
                    found.extend(iter_images(item))
        for key in ("url", "image"):
            v = obj.get(key)
            if isinstance(v, str) and v.startswith(("http://", "https://")):
                found.append(("url", v))
        v = obj.get("b64_json")
        if isinstance(v, str) and v:
            found.append(("b64", v))
    elif isinstance(obj, list):
        for item in obj:
            found.extend(iter_images(item))
    return found


def cmd_save(args):
    raw = Path(args.response).read_bytes()
    try:
        data = json.loads(raw.decode("utf-8", "replace"))
    except ValueError:
        die("响应不是 JSON（前 200 字节）：%s" % raw[:200])

    if isinstance(data, dict):
        if data.get("error"):
            out(data["error"])
            die("服务端返回 error，别用同样的参数重试")
        if data.get("code") and not data.get("data"):
            die("失败：%s / %s" % (data.get("code"), data.get("message")))
        if data.get("status") in ("queued", "running") or data.get("state") in ("waiting", "generating"):
            out({"task_id": data.get("task_id"), "status": data.get("status"), "state": data.get("state")})
            die("任务还没完成，用 poll 查同一个 task_id，不要重新提交（重复提交会再计费）")

    items = iter_images(data)
    if not items:
        out({"hint": "没找到图片字段", "top_level_keys": list(data.keys()) if isinstance(data, dict) else type(data).__name__})
        die("结构不匹配")

    outdir = Path(args.out_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    for idx in range(1, len(items) + 1):
        check_output(outdir / ("image-%02d.png" % idx))
    report = []
    for idx, (kind, value) in enumerate(items, 1):
        name = "image-%02d.png" % idx
        target = outdir / name
        if kind == "b64":
            payload = value.split(",", 1)[-1] if value.startswith("data:") else value
            try:
                blob = base64.b64decode(payload)
            except Exception as exc:  # noqa: BLE001
                report.append({"file": name, "ok": False, "error": "base64 解不开：%s" % exc})
                continue
            target.write_bytes(blob)
        else:
            ok, info = curl_download(value, target)
            if not ok:
                report.append({"file": name, "ok": False, "error": info})
                continue
        size = image_size(target)
        entry = {"file": str(target), "bytes": target.stat().st_size}
        if size:
            entry.update({"width": size[0], "height": size[1], "format": size[2]})
            if args.expect_size:
                ew, eh = parse_size(args.expect_size)
                if ew and (size[0], size[1]) != (ew, eh):
                    entry["size_mismatch"] = "请求 %dx%d，实际 %dx%d" % (ew, eh, size[0], size[1])
        report.append(entry)
    out(report)


def cmd_size(args):
    for f in args.files:
        r = image_size(f)
        if r:
            sys.stdout.write("%s  %dx%d  %s\n" % (f, r[0], r[1], r[2]))
        else:
            sys.stdout.write("%s  读不出尺寸（只支持 PNG / JPEG；也可能是空文件或错误页）\n" % f)


def cmd_overlay(args):
    """给图片叠中文。模型写的中文一律糊，叠字才靠谱。"""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        die("需要 Pillow：pip install pillow")

    src = Path(args.image)
    if not src.is_file():
        die("找不到图片：%s" % src)
    img = Image.open(src).convert("RGBA")

    font_path = args.font or os.environ.get("IMAGE_FONT")
    if not font_path or not Path(font_path).is_file():
        die("找不到字体：用 --font 指定可读的中文 TTF/OTF/TTC 文件，或设置 IMAGE_FONT")
    try:
        ImageFont.truetype(font_path, args.font_size)
    except OSError:
        die("字体无法加载：%s；请检查字体格式及读取权限" % font_path)

    text = args.text
    size = args.font_size
    while True:
        font = ImageFont.truetype(font_path, size)
        box = font.getbbox(text)
        w = box[2] - box[0]
        if w <= img.width - 40 or size <= 12:
            break
        size -= 4
    box = font.getbbox(text)
    w, h = box[2] - box[0], box[3] - box[1]

    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    x = (img.width - w) // 2 if args.align == "center" else 40
    y = args.y if args.y is not None else (img.height - h) // 2
    if args.bg:
        draw.rectangle([x - 20, y - 12, x + w + 20, y + h + 12], fill=(*args.bg, 190))
    draw.text((x - box[0], y - box[1]), text, font=font, fill=(*args.fg, 255))
    out_img = Image.alpha_composite(img, layer)
    target = Path(args.out) if args.out else src.with_name(src.stem + "-text" + src.suffix)
    check_output(target)
    out_img.convert("RGB").save(target)
    size_info = image_size(target)
    out({"file": str(target), "font_size": size, "text_width": w,
         "size": "%dx%d" % (size_info[0], size_info[1]) if size_info else None})


# ---------------------------------------------------------------- 自检

def cmd_self_test(args):
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        sys.stdout.write("[%s] %s%s\n" % ("PASS" if cond else "FAIL", name, ("  " + detail) if detail else ""))
        if not cond:
            ok = False

    # 1. size 解析
    check("size 解析 1024x1536", parse_size("1024x1536") == (1024, 1536))
    check("size 解析 auto", parse_size("auto") == (None, None))
    check("size 解析非法值", parse_size("1024*1536") == (None, None))

    # 2. 校验：sub 的非标准档位只提示不拦
    p, n = validate("sub", "gpt-image-2", "2048x1152", 1, "x", None)
    check("sub 非标准档位给提示", p == [] and any("历史" in x for x in n), str(n))

    # 3. 校验：缺 model 被拦
    p, _ = validate("sub", "", "1024x1024", 1, "x", None)
    check("缺 model 被拦", any("model" in x for x in p), str(p))

    # 4. 校验：n 过大被拦
    p, _ = validate("sub", "gpt-image-2", "1024x1024", 9, "x", None)
    check("n 过大被拦", any("n " in x or "4 张" in x for x in p), str(p))

    # 5. 请求体：sub
    b = build_body("sub", "gpt-image-2", "一只橘猫", "1024x1536", 1)
    check("sub 请求体字段", b == {"model": "gpt-image-2", "prompt": "一只橘猫", "size": "1024x1536", "n": 1}, str(b))

    # 6. 请求体：rrw
    b = build_body("rrw", "your-image-model", "一只白杯", "1024x1024", 1,
                   quality="high", output_format="png", image_size="1K",
                   idempotency_key="k1")
    check("rrw 请求体字段", b.get("quality") == "high" and b.get("output_format") == "png"
          and b.get("image_size") == "1K", str(b))
    check("rrw 幂等键单列", b.get("_idempotency_key") == "k1", str(b))

    # 7. 响应解析：三种形态
    for name, s in {
        "sub b64": {"data": [{"b64_json": "AAAA", "url": ""}]},
        "sub url": {"data": [{"url": "https://x/a.png"}]},
        "rrw 任务成功": {"task_id": 1, "status": "succeeded",
                          "data": [{"resource_id": 31, "url": "https://x/a.png"}]},
    }.items():
        check("解析 %s" % name, len(iter_images(s)) >= 1, str(iter_images(s)))

    # 8. 空 b64 不能当成有图
    check("空 b64_json 不算图", len(iter_images({"data": [{"b64_json": "", "url": ""}]})) == 0)

    # 9. PNG 头读取
    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8AAAwAB/wFbCwAAAABJRU5ErkJggg==")
    with tempfile.TemporaryDirectory(prefix="opc-design-selftest-") as td:
        tmp = Path(td) / "image.png"
        tmp.write_bytes(png)
        r = image_size(tmp)
        check("读 PNG 头", r is not None and r[0] >= 1, str(r))

    check("curl 默认尊重代理", "--noproxy" not in to_curl("sub", "https://x", {}))
    check("curl 带可配置 UA", UA in to_curl("sub", "https://x", {}))
    check("rrw curl 带幂等键头", "Idempotency-Key" in to_curl("rrw", "https://x", {"_idempotency_key": "k"}))
    check("curl 里没有明文 Key", "sk-" not in to_curl("sub", "https://x", {}))

    sys.stdout.write("\n%s\n" % ("自检全部通过。" if ok else "有检查项未通过。"))
    raise SystemExit(0 if ok else 1)


# ---------------------------------------------------------------- CLI

def main(argv=None):
    global CONFIG_PATH, ALLOW_LEGACY_CONFIG, OVERWRITE, NO_PROXY, UA
    ap = argparse.ArgumentParser(prog="image_api.py", description="站点配图出图工具（两个供应商）")
    ap.add_argument("--config", type=Path, default=CONFIG_PATH, help="配置文件路径（放在子命令前）")
    ap.add_argument("--allow-legacy-config", action="store_true", help="明确允许读取旧技能配置")
    ap.add_argument("--no-proxy", help="显式直连的主机列表；默认尊重系统代理")
    ap.add_argument("--user-agent", default=UA)
    ap.add_argument("--overwrite", action="store_true", help="明确允许覆盖输出")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("self-test", help="离线自检")
    p.set_defaults(func=cmd_self_test)

    p = sub.add_parser("providers", help="看两个供应商的配置状态")
    p.set_defaults(func=cmd_providers)

    p = sub.add_parser("init", help="保存某家的地址与 Key")
    p.add_argument("--provider", required=True, choices=provider_ids())
    p.add_argument("--base-url")
    p.add_argument("--key")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("models", help="列可用模型")
    p.add_argument("--provider", default="sub", choices=provider_ids())
    p.add_argument("--base-url")
    p.add_argument("--key")
    p.set_defaults(func=cmd_models)

    p = sub.add_parser("quote", help="询价（仅 rrw）")
    p.add_argument("--provider", default="rrw", choices=provider_ids())
    p.add_argument("--model")
    p.add_argument("--prompt")
    p.add_argument("--size")
    p.add_argument("--n", type=int)
    p.add_argument("--quality")
    p.add_argument("--image-size")
    p.add_argument("--aspect-ratio")
    p.add_argument("--base-url")
    p.add_argument("--key")
    p.set_defaults(func=cmd_quote)

    p = sub.add_parser("plan", help="出图计划：把站点配图拆成一组任务")
    p.add_argument("--scene", help="如 门店 / 产品 / 个人")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_plan)

    p = sub.add_parser("build", help="构造请求体（离线）")
    p.add_argument("--provider", default="sub", choices=provider_ids())
    p.add_argument("--model")
    p.add_argument("--prompt")
    p.add_argument("--size")
    p.add_argument("--n", type=int)
    p.add_argument("--response-format", choices=["url", "b64_json"])
    p.add_argument("--quality")
    p.add_argument("--image-size")
    p.add_argument("--aspect-ratio")
    p.add_argument("--output-format")
    p.add_argument("--image-reference-id", type=int, action="append")
    p.add_argument("--image", nargs="*")
    p.add_argument("--callback-url")
    p.add_argument("--idempotency-key")
    p.add_argument("--out", required=True)
    p.add_argument("--base-url")
    p.add_argument("--key")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("send", help="发请求")
    p.add_argument("--provider", default="sub", choices=provider_ids())
    p.add_argument("--request", help="已有请求体文件")
    p.add_argument("--model")
    p.add_argument("--prompt")
    p.add_argument("--size")
    p.add_argument("--n", type=int)
    p.add_argument("--response-format", choices=["url", "b64_json"])
    p.add_argument("--quality")
    p.add_argument("--image-size")
    p.add_argument("--aspect-ratio")
    p.add_argument("--output-format")
    p.add_argument("--image-reference-id", type=int, action="append")
    p.add_argument("--image", nargs="*")
    p.add_argument("--callback-url")
    p.add_argument("--idempotency-key")
    p.add_argument("--base-url")
    p.add_argument("--key")
    p.add_argument("--timeout", type=int, default=480)
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_send)

    p = sub.add_parser("poll", help="轮询任务（仅 rrw）")
    p.add_argument("--provider", default="rrw", choices=provider_ids())
    p.add_argument("--task-id", required=True)
    p.add_argument("--max-wait", type=int, default=900)
    p.add_argument("--out-dir", default="out")
    p.add_argument("--out")
    p.add_argument("--base-url")
    p.add_argument("--key")
    p.set_defaults(func=cmd_poll)

    p = sub.add_parser("upload", help="上传参考图（仅 rrw）")
    p.add_argument("--provider", default="rrw", choices=provider_ids())
    p.add_argument("--file", required=True)
    p.add_argument("--base-url")
    p.add_argument("--key")
    p.set_defaults(func=cmd_upload)

    p = sub.add_parser("save", help="解析响应落盘并核对尺寸")
    p.add_argument("--response", required=True)
    p.add_argument("--out-dir", default="out")
    p.add_argument("--expect-size")
    p.set_defaults(func=cmd_save)

    p = sub.add_parser("size", help="读图片真实宽高")
    p.add_argument("files", nargs="+")
    p.set_defaults(func=cmd_size)

    p = sub.add_parser("overlay", help="给图片叠中文")
    p.add_argument("--image", required=True)
    p.add_argument("--text", required=True)
    p.add_argument("--out")
    p.add_argument("--font", help="中文字体文件路径，也可设置 IMAGE_FONT")
    p.add_argument("--font-size", type=int, default=64)
    p.add_argument("--align", choices=["center", "left"], default="center")
    p.add_argument("--y", type=int)
    p.add_argument("--fg", type=int, nargs=3, default=[255, 255, 255])
    p.add_argument("--bg", type=int, nargs=3)
    p.set_defaults(func=cmd_overlay)

    args = ap.parse_args(argv)
    CONFIG_PATH = args.config.expanduser()
    ALLOW_LEGACY_CONFIG = args.allow_legacy_config
    OVERWRITE = args.overwrite
    NO_PROXY = args.no_proxy
    UA = args.user_agent
    if getattr(args, "out", None):
        check_output(args.out)
        for name in ("request", "response", "image"):
            source = getattr(args, name, None)
            if isinstance(source, str) and Path(source).resolve() == Path(args.out).resolve():
                die("输入与输出不能是同一路径")
    args.func(args)


if __name__ == "__main__":
    main()
