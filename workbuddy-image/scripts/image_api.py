#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""image_api.py —— 图片生成接口的本地工具（零第三方依赖，仅标准库，Python 3.8+）

九件事，按「需不需要 Key」分三组：

  一次配置（让后面的命令不用每次都传地址和 Key）
    init        交互式或参数式保存接口地址与 Key 到 ~/.aigc-image/config.json
                init --show 查看当前配置（Key 打码）

  离线就能跑（沙箱 / 没 Key 也能出结果）
    presets     列出常用尺寸模板：公众号封面、小红书封面、海报、头像等
    self-test   自检：跑内置样例，验证参数校验、请求体构造、尺寸读取都正常
    validate    校验参数：模型名、size 格式与像素范围、宽高比、n 的取值
    build       构造请求体，输出 JSON 与等价 curl（不发请求、不花 token）
    size        读图片文件头，报真实宽高

  需要接口地址和 Key（不传就用 init 存下来的）
    probe       GET {base}/models，列出可用模型并标出图片类
    send        发送已构造好的请求体，保存原始响应，报 HTTP 码与耗时
    save        解析响应里的 url 或 base64，落盘，并核对真实尺寸是否与请求一致

常用串联：

  python image_api.py self-test
  python image_api.py init --base-url https://your-host/v1 --key sk-xxx
  python image_api.py validate --proto openai --model gpt-image-2 --size 1024x1536
  python image_api.py build --proto openai --model gpt-image-2 --prompt "一只橘猫" --size 1024x1536 --out req.json
  python image_api.py send --proto openai --request req.json --out resp.json
  python image_api.py save --response resp.json --out-dir out --expect-size 1024x1536
  python image_api.py size out/image-01.png

地址与 Key 的读取优先级：命令行参数 > 环境变量（IMAGE_BASE_URL / IMAGE_API_KEY）> init 保存的配置文件。
配置文件只存在本机用户目录，权限尽力设为 0600；里面是明文 Key，别提交到 Git、别放进共享目录。
Key 不会写进请求体、响应、报告或日志。
"""

import argparse
import base64
import json
import os
import re
import struct
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(errors="replace")
        sys.stderr.reconfigure(errors="replace")
    except Exception:
        pass

# ---------------------------------------------------------------- 常量

PROTOS = ("openai", "openai-edit", "dashscope", "dashscope-async")

# size 分隔符：OpenAI 用字母 x，DashScope 用星号 *
SEP = {"openai": "x", "openai-edit": "x", "dashscope": "*", "dashscope-async": "*"}

# gpt-image 系的固定档位（OpenAI 官方口径），其余模型走范围校验
GPT_SIZES = {
    "1024x1024", "1536x1024", "1024x1536", "auto",
    "512x512", "256x256",
}

QWEN_IMAGE_MODELS = {
    "qwen-image-3.0-pro", "qwen-image-3.0",
    "qwen-image-2.1-pro", "qwen-image-2.1-turbo",
}

# 已知模型的参考图上限（3.0 系 3 张，2.1 系 10 张）
QWEN_MAX_IMAGES = {"3.0": 3, "2.1": 10}

MIN_PIXELS = 512 * 512
MAX_PIXELS = 2048 * 2048
MIN_RATIO = 1.0 / 8
MAX_RATIO = 8.0

# 配置文件：只存本机用户目录，记录接口地址与 Key，省得每次命令都传
CONFIG_PATH = Path.home() / ".aigc-image" / "config.json"

# 常用尺寸模板。内容一律留空由用户补，这里只给尺寸、比例和风格骨架。
# size 全部落在 512x512 ~ 2048x2048 且宽高比 1:8~8:1 之内，两家协议都能过。
PRESETS = [
    {
        "id": "wechat-cover",
        "scene": "公众号封面首图",
        "size": "1536x1024",
        "aspect": "3:2",
        "style": "简洁商业摄影，主体偏右，左侧大面积留白放标题",
        "prompt": "【用户补充的内容】，简约商业摄影风格，主体居中偏右，左侧大面积留白用于放标题，柔和自然光，浅色干净背景，画面里不要出现文字",
        "note": "公众号官方封面是 2.35:1，两家接口都不直接支持，出图后按 900x383 裁切",
    },
    {
        "id": "wechat-inline",
        "scene": "公众号正文配图",
        "size": "1024x1024",
        "aspect": "1:1",
        "style": "扁平插画，信息图感，配色克制",
        "prompt": "【用户补充的内容】，扁平矢量插画风格，构图简洁，留白充足，配色克制（主色不超过三种），适合作为文章配图",
        "note": "正文里多图并排，方图裁切损耗最小",
    },
    {
        "id": "xhs-cover",
        "scene": "小红书封面",
        "size": "1024x1536",
        "aspect": "2:3",
        "style": "竖版，上方留标题区，对比强烈，生活感",
        "prompt": "【用户补充的内容】，竖版构图，画面上方三分之一留出干净区域用于加标题，主体清晰，色彩明快，生活化质感，高清细节",
        "note": "小红书主流是 3:4，接口只给 2:3，出图后上下各裁一点即接近 3:4",
    },
    {
        "id": "xhs-photo",
        "scene": "小红书实拍感配图",
        "size": "1024x1024",
        "aspect": "1:1",
        "style": "手机实拍，自然光，不摆拍",
        "prompt": "【用户补充的内容】，手机随手拍质感，自然光，轻微景深，画面真实不做作，细节丰富，非棚拍",
        "note": "要「不像 AI 生成」就用这个，别加「高清、8K、masterpiece」这类词",
    },
    {
        "id": "poster",
        "scene": "竖版海报",
        "size": "1024x1536",
        "aspect": "2:3",
        "style": "商业海报，主体突出，留标题位",
        "prompt": "【用户补充的内容】，商业海报构图，主体占画面中部，上方或下方留出标题与卖点区域，光线有层次，材质真实，画面里不要出现文字",
        "note": "文字后期加，让模型直接写字容易糊",
    },
    {
        "id": "avatar",
        "scene": "头像或人物图",
        "size": "1024x1024",
        "aspect": "1:1",
        "style": "半身，简洁背景，正面光",
        "prompt": "【用户补充的内容】，半身构图，正面或四分之三侧面，简洁纯色背景，柔和正面光，五官清晰，表情自然",
        "note": "做头像时人物要居中，四周留够裁切余量",
    },
]


# ---------------------------------------------------------------- 配置

def load_config():
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def resolve_base_url(cli_value):
    """优先级：命令行 > 环境变量 > 配置文件。"""
    if cli_value:
        return cli_value.rstrip("/")
    env = os.environ.get("IMAGE_BASE_URL", "").strip()
    if env:
        return env.rstrip("/")
    cfg = load_config().get("base_url", "")
    return cfg.rstrip("/") if isinstance(cfg, str) else ""


def resolve_key(cli_value):
    if cli_value:
        return cli_value.strip()
    env = os.environ.get("IMAGE_API_KEY", "").strip()
    if env:
        return env
    cfg = load_config().get("api_key", "")
    return cfg.strip() if isinstance(cfg, str) else ""


def mask(key):
    """展示用：只留前 4 位和后 4 位。"""
    if not key:
        return "(未设置)"
    if len(key) <= 12:
        return key[:2] + "*" * max(len(key) - 2, 0)
    return "%s...%s" % (key[:4], key[-4:])


def cmd_init(args):
    cfg = load_config()

    if args.show:
        out({
            "config_path": str(CONFIG_PATH),
            "exists": CONFIG_PATH.exists(),
            "base_url": cfg.get("base_url") or "(未设置)",
            "api_key": mask(cfg.get("api_key", "")),
            "updated_at": cfg.get("updated_at", ""),
        })
        sys.stdout.write("\nKey 是明文存在本机，别提交到 Git 或放进共享目录。\n")
        return

    base_url = (args.base_url or "").strip().rstrip("/")
    key = (args.key or "").strip()

    # 参数不全时走交互；stdin 不是终端就报错，避免在沙箱里卡死
    if not base_url or not key:
        if not sys.stdin.isatty():
            die("非交互环境，请用参数直接指定：init --base-url <URL> --key <KEY>")
        sys.stdout.write("配置接口地址与 Key（直接回车保留原值）。\n\n")
        if not base_url:
            hint = ("当前：%s" % cfg.get("base_url")) if cfg.get("base_url") else "例：https://your-host/v1"
            sys.stdout.write("接口地址（%s）：" % hint)
            line = sys.stdin.readline().strip()
            base_url = line.rstrip("/") if line else cfg.get("base_url", "")
        if not key:
            hint = ("当前：%s" % mask(cfg.get("api_key", ""))) if cfg.get("api_key") else "例：sk-xxxx"
            sys.stdout.write("API Key（%s）：" % hint)
            line = sys.stdin.readline().strip()
            key = line if line else cfg.get("api_key", "")

    if not base_url:
        die("接口地址不能为空。OpenAI 兼容接口一般形如 https://your-host/v1")
    if not key:
        die("Key 不能为空")

    cfg["base_url"] = base_url
    cfg["api_key"] = key
    cfg["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        os.chmod(CONFIG_PATH, 0o600)  # Windows 上只改只读位，失败就算了
    except OSError:
        pass

    out({"saved_to": str(CONFIG_PATH), "base_url": base_url, "api_key": mask(key)})
    sys.stdout.write("\n已保存，之后 probe / send 不用再传地址和 Key。\n")
    sys.stdout.write("这是明文文件，别提交到 Git。要核对模型列表就跑：probe\n")


def die(msg, code=2):
    sys.stderr.write("error: %s\n" % msg)
    raise SystemExit(code)


def out(obj):
    if isinstance(obj, (dict, list)):
        sys.stdout.write(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")
    else:
        sys.stdout.write(str(obj) + "\n")


# ---------------------------------------------------------------- 参数校验

def parse_size(value, sep):
    """把 '1024x1536'（OpenAI）或 '1024*1536'（DashScope）解析成 (w, h) 或 None。

    只认当前协议的分隔符：OpenAI 用字母 x，DashScope 用星号 *。
    两种写反了是迁移时最常见的错，必须拦下来而不是宽容解析。
    """
    if value is None:
        return None, None
    v = value.strip().lower()
    if v == "auto":
        return None, None
    m = re.match(r"^(\d{1,5})\s*%s\s*(\d{1,5})$" % re.escape(sep), v)
    if not m:
        return None, None
    return int(m.group(1)), int(m.group(2))


def validate(args):
    """返回 (问题列表, 提示列表)。问题为空即通过。"""
    problems, notes = [], []
    proto = args.proto
    model = args.model or ""
    sep = SEP[proto]
    is_qwen = model.lower().startswith("qwen-image")

    w, h = parse_size(args.size, sep)
    if args.size:
        if args.size.strip().lower() == "auto":
            if proto in ("dashscope", "dashscope-async"):
                notes.append("百炼协议没有 auto 写法，不传 size 即由模型自动推荐分辨率")
        elif w is None:
            problems.append(
                "size 解析失败：%r。%s 协议用 %r 做分隔符（如 1024%s1024），不是另一种"
                % (args.size, proto, sep, sep)
            )
        else:
            area = w * h
            if proto == "openai" and not is_qwen:
                if args.size not in GPT_SIZES:
                    notes.append(
                        "非 gpt-image 标准档位 %s，服务端常静默改成正方形；出图后务必用 size 子命令核对" % args.size
                    )
            if is_qwen or proto.startswith("dashscope"):
                if area < MIN_PIXELS:
                    problems.append("size 面积 %d 小于下限 %d（512%s512）" % (area, MIN_PIXELS, sep))
                if area > MAX_PIXELS:
                    problems.append("size 面积 %d 超过上限 %d（2048%s2048）" % (area, MAX_PIXELS, sep))
                ratio = max(w, h) / float(min(w, h))
                if ratio < MIN_RATIO or ratio > MAX_RATIO:
                    problems.append("宽高比 %s 超出 1:8 ~ 8:1" % args.size)

    if args.n is not None:
        if args.n < 1:
            problems.append("n 必须 >= 1")
        if is_qwen or proto.startswith("dashscope"):
            if args.n > 6:
                problems.append("qwen-image 系 n 上限为 6，当前 %d" % args.n)
        elif args.n > 10:
            problems.append("n 取值过大（%d），一次别超过 10，先跑通 1 张" % args.n)
        if args.n > 1:
            notes.append("多图会成倍计费且耗时明显变长，先跑通 n=1 再加")

    if not model:
        problems.append("缺 model：模型名从 {base}/models 返回的 id 里取，不要凭印象拼")

    if proto.startswith("dashscope") and not is_qwen:
        notes.append("百炼协议目前只服务 qwen-image 系列，模型名 %r 请再核对" % model)
    if is_qwen and proto in ("openai", "openai-edit"):
        notes.append(
            "qwen 走 OpenAI 兼容模式时：图生图用 generations 的 image 字段，不用 /images/edits；"
            "response_format=b64_json 会被忽略，只回 url；没有异步"
        )
    if args.image and is_qwen:
        n_img = len(args.image)
        for key, cap in QWEN_MAX_IMAGES.items():
            if key in model:
                if n_img > cap:
                    problems.append("%s 系最多 %d 张参考图，当前 %d 张" % (key, cap, n_img))
                break
    if proto == "openai-edit" and not args.image:
        problems.append("图生图（/images/edits）必须给 --image")
    if args.image and not is_qwen and len(args.image) > 1:
        notes.append("非 qwen 模型的多图输入支持情况不一，先试单张")

    return problems, notes


# ---------------------------------------------------------------- 请求体构造

def build_body(args):
    proto, model = args.proto, args.model
    payload = {"model": model}

    if proto in ("openai", "openai-edit"):
        payload["prompt"] = args.prompt
        if args.size:
            payload["size"] = args.size
        if args.n is not None:
            payload["n"] = args.n
        if args.response_format and proto == "openai":
            payload["response_format"] = args.response_format
        if args.image:
            if proto == "openai":
                # 兼容模式：image 是扩展字段，单张传字符串、多张传数组
                payload["image"] = args.image[0] if len(args.image) == 1 else args.image
            else:
                payload["_multipart_image"] = args.image  # 由 send 转成 multipart
        return payload

    # dashscope / dashscope-async
    content = []
    for img in args.image or []:
        content.append({"image": img})
    if args.prompt:
        content.append({"text": args.prompt})
    if not content:
        die("百炼协议需要一个 text（文生图）或 image+text（图生图）")
    payload["input"] = {"messages": [{"role": "user", "content": content}]}
    params = {}
    if args.size:
        params["size"] = args.size
    if args.n is not None:
        params["n"] = args.n
    if args.negative_prompt:
        params["negative_prompt"] = args.negative_prompt
    if args.seed is not None:
        params["seed"] = args.seed
    if args.watermark:
        params["watermark"] = True
    if params:
        payload["parameters"] = params
    return payload


def to_curl(args, body):
    """生成等价 curl，方便用户自己复制去跑。Key 用环境变量占位，不落明文。"""
    proto = args.proto
    if proto == "openai":
        url = "$IMAGE_BASE_URL/images/generations"
    elif proto == "openai-edit":
        url = "$IMAGE_BASE_URL/images/edits"
    elif proto == "dashscope":
        url = "$DASHSCOPE_BASE_URL/api/v1/services/aigc/multimodal-generation/generation"
    else:
        url = "$DASHSCOPE_BASE_URL/api/v1/services/aigc/image-generation/generation"

    lines = [
        "curl -sS --noproxy '*' --max-time 480 -X POST \"%s\" \\" % url,
        "  -H \"Authorization: Bearer $IMAGE_API_KEY\" \\",
        "  -H \"Content-Type: application/json\" \\",
    ]
    if proto == "dashscope-async":
        lines.insert(2, "  -H \"X-DashScope-Async: enable\" \\")
    if proto == "openai-edit":
        lines = [
            "curl -sS --noproxy '*' --max-time 480 -X POST \"%s\" \\" % url,
            "  -H \"Authorization: Bearer $IMAGE_API_KEY\" \\",
        ]
        for k, v in body.items():
            if k == "_multipart_image":
                for p in v:
                    # 本地文件用 @，公网 URL 直接传值
                    val = p if p.startswith(("http://", "https://", "data:")) else "@%s" % p
                    lines.append("  -F \"image=%s\" \\" % val)
            else:
                lines.append("  -F \"%s=%s\" \\" % (k, v))
        lines.append("  -o response.json -w 'http=%%{http_code} time=%%{time_total}s\\n'")
        return "\n".join(lines)

    lines.append("  --data-binary '@request.json' \\")
    lines.append("  -o response.json -w 'http=%{http_code} time=%{time_total}s\\n'")
    return "\n".join(lines)


# ---------------------------------------------------------------- 网络

def encode_multipart(fields, file_paths):
    """把字段与本地图片编成 multipart/form-data，返回 (bytes, content_type)。"""
    import uuid
    boundary = "----image_api_%s" % uuid.uuid4().hex
    buf = b""
    for k, v in fields.items():
        buf += ("--%s\r\n" % boundary).encode("utf-8")
        buf += ('Content-Disposition: form-data; name="%s"\r\n\r\n' % k).encode("utf-8")
        buf += (str(v) + "\r\n").encode("utf-8")
    for path in file_paths:
        p = Path(path)
        if not p.exists():
            die("找不到输入图：%s" % path)
        buf += ("--%s\r\n" % boundary).encode("utf-8")
        buf += ('Content-Disposition: form-data; name="image"; filename="%s"\r\n' % p.name).encode("utf-8")
        buf += b"Content-Type: image/png\r\n\r\n"
        buf += p.read_bytes() + b"\r\n"
    buf += ("--%s--\r\n" % boundary).encode("utf-8")
    return buf, "multipart/form-data; boundary=%s" % boundary


def http_send(url, key, raw=None, content_type=None, timeout=480, headers=None, method=None):
    """底层发送：raw 为 None 走 GET，否则按 content_type 发 POST。"""
    req_headers = {"Authorization": "Bearer %s" % key}
    if content_type:
        req_headers["Content-Type"] = content_type
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, data=raw, headers=req_headers, method=method or ("POST" if raw else "GET"))
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    t0 = time.time()
    try:
        with opener.open(req, timeout=timeout) as resp:
            return resp.status, resp.read(), time.time() - t0
    except urllib.error.HTTPError as e:
        return e.code, e.read(), time.time() - t0


def http_json(url, key, data=None, timeout=480, headers=None, method=None):
    req_headers = {"Authorization": "Bearer %s" % key}
    if data is not None:
        req_headers["Content-Type"] = "application/json"
    if headers:
        req_headers.update(headers)
    raw = json.dumps(data, ensure_ascii=False).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=raw, headers=req_headers, method=method or ("POST" if raw else "GET"))
    # 本机系统代理会拦 127.0.0.1 与部分外网，这里显式不走代理
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    t0 = time.time()
    try:
        with opener.open(req, timeout=timeout) as resp:
            body = resp.read()
            return resp.status, body, time.time() - t0
    except urllib.error.HTTPError as e:
        return e.code, e.read(), time.time() - t0


def cmd_probe(args):
    url = args.base_url.rstrip("/") + "/models"
    code, body, secs = http_json(url, args.key, timeout=60)
    sys.stdout.write("http=%d time=%.1fs\n" % (code, secs))
    if code != 200:
        sys.stdout.write(body.decode("utf-8", "replace")[:2000] + "\n")
        raise SystemExit(1 if code >= 400 else 0)
    try:
        data = json.loads(body.decode("utf-8", "replace"))
    except ValueError:
        sys.stdout.write("响应不是 JSON，可能不是 OpenAI 兼容地址：\n" + body.decode("utf-8", "replace")[:500] + "\n")
        raise SystemExit(1)
    ids = [m.get("id", "") for m in data.get("data", []) if isinstance(m, dict)]
    if not ids:
        sys.stdout.write("没有解析到 data[].id，返回结构：\n" + json.dumps(data, ensure_ascii=False)[:500] + "\n")
        raise SystemExit(1)
    # 只按「名字里带图片语义」筛，别用 qwen/wan 这种厂商词，否则会把 qwen3.5-flash 这类文本模型也带进来
    kw = ("image", "dall", "flux", "imagen", "seedream", "kolors", "canvas", "draw")
    hits = [i for i in ids if any(k in i.lower() for k in kw)]
    out({"total_models": len(ids), "image_like": hits, "all": ids})
    sys.stdout.write("\n提示：名字像不代表能出图。挑一个用 build + send 实跑一次再下结论；\n")
    sys.stdout.write("聊天类、embedding 类模型不会出现在上面的 image_like 里。\n")


def cmd_send(args):
    body = json.loads(Path(args.request).read_text(encoding="utf-8"))
    proto = args.proto
    if proto == "openai":
        url = args.base_url.rstrip("/") + "/images/generations"
    elif proto == "openai-edit":
        url = args.base_url.rstrip("/") + "/images/edits"
    elif proto == "dashscope":
        url = args.base_url.rstrip("/") + "/api/v1/services/aigc/multimodal-generation/generation"
    else:
        url = args.base_url.rstrip("/") + "/api/v1/services/aigc/image-generation/generation"

    headers = {"X-DashScope-Async": "enable"} if proto == "dashscope-async" else None
    if proto == "openai-edit":
        fields = {k: v for k, v in body.items() if k != "_multipart_image"}
        paths = body.get("_multipart_image", [])
        raw_body, ctype = encode_multipart(fields, paths)
        code, raw, secs = http_send(url, args.key, raw=raw_body, content_type=ctype,
                                    timeout=args.timeout, headers=headers)
    else:
        code, raw, secs = http_json(url, args.key, data=body, timeout=args.timeout, headers=headers)
    sys.stdout.write("http=%d time=%.1fs bytes=%d\n" % (code, secs, len(raw)))
    Path(args.out).write_bytes(raw)
    sys.stdout.write("原始响应已存 %s（Key 没有写进去）\n" % args.out)
    if code != 200:
        sys.stdout.write(raw.decode("utf-8", "replace")[:1500] + "\n")
    raise SystemExit(0 if code == 200 else 1)


# ---------------------------------------------------------------- 解析与落盘

def image_size(path):
    """读 PNG / JPEG 头取真实宽高，返回 (w, h, fmt)；不是图片就返回 None。"""
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
    if raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        return None
    return None


def iter_images(obj):
    """从响应里尽量找出图片：url 或 base64。兼容 OpenAI、百炼、以及常见的改包结构。"""
    found = []
    if isinstance(obj, dict):
        for key in ("url", "image", "b64_json"):
            pass
        # OpenAI: data[].url / data[].b64_json
        if isinstance(obj.get("data"), list):
            for item in obj["data"]:
                if isinstance(item, dict):
                    found.extend(iter_images(item))
        # 百炼: output.choices[].message.content[].image
        choices = (obj.get("output") or {}).get("choices") if isinstance(obj.get("output"), dict) else None
        if isinstance(choices, list):
            for c in choices:
                found.extend(iter_images((c or {}).get("message", {})))
        for key in ("content", "results", "images"):
            v = obj.get(key)
            if isinstance(v, list):
                for item in v:
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

    if isinstance(data, dict) and data.get("error"):
        out(data["error"])
        die("服务端返回 error，不要重试同样的参数")
    if isinstance(data, dict) and data.get("code"):
        die("失败：%s / %s（request_id: %s）" % (data.get("code"), data.get("message"), data.get("request_id")))

    status = (data.get("output") or {}).get("task_status") if isinstance(data.get("output"), dict) else None
    if status and status != "SUCCEEDED":
        out({"task_status": status, "task_id": (data.get("output") or {}).get("task_id")})
        sys.stdout.write("任务还没完成，用 task_id 继续轮询，不要重新提交（重复提交会再次计费）。\n")
        return

    items = iter_images(data)
    if not items:
        out({"hint": "没找到图片字段", "top_level_keys": list(data.keys()) if isinstance(data, dict) else type(data).__name__})
        die("结构不匹配：把原始响应贴出来，对着 references/openai-compatible.md 或 references/dashscope.md 核对结构")

    outdir = Path(args.out_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    report = []
    for idx, (kind, value) in enumerate(items, 1):
        name = "image-%02d.png" % idx
        try:
            if kind == "b64":
                payload = value.split(",", 1)[-1] if value.startswith("data:") else value
                blob = base64.b64decode(payload)
            else:
                with opener.open(value, timeout=180) as r:
                    blob = r.read()
        except Exception as e:
            report.append({"file": name, "ok": False, "error": str(e)})
            continue
        if blob[:1] == b"<" or len(blob) < 1000:
            report.append({"file": name, "ok": False, "error": "内容不像图片（%d 字节），多半存成了错误页" % len(blob)})
            continue
        p = outdir / name
        p.write_bytes(blob)
        size = image_size(p)
        entry = {"file": str(p), "bytes": len(blob)}
        if size:
            entry.update({"width": size[0], "height": size[1], "format": size[2]})
            if args.expect_size:
                ew, eh = parse_size(args.expect_size, "x")
                if ew and (size[0], size[1]) != (ew, eh):
                    entry["size_mismatch"] = "请求 %sx%s，实际 %sx%s" % (ew, eh, size[0], size[1])
        report.append(entry)
    out(report)


def cmd_size(args):
    for f in args.files:
        r = image_size(f)
        if r:
            sys.stdout.write("%s  %dx%d  %s\n" % (f, r[0], r[1], r[2]))
        else:
            sys.stdout.write("%s  读不出尺寸（只支持 PNG / JPEG；也可能是空文件或错误页）\n" % f)


# ---------------------------------------------------------------- 自检

def cmd_presets(args):
    """列出常用尺寸模板。内容留空，只给尺寸、比例和风格骨架。"""
    items = PRESETS
    if args.id:
        items = [p for p in items if p["id"] == args.id]
        if not items:
            die("没有这个模板：%s。可用：%s" % (args.id, ", ".join(p["id"] for p in PRESETS)))
    if args.scene:
        items = [p for p in items if args.scene in p["scene"]]
        if not items:
            die("没有匹配「%s」的模板，去掉 --scene 看全部" % args.scene)

    if args.json or args.id:
        out(items)
        if args.id:
            sys.stdout.write("\n把提示词里的【用户补充的内容】换成你要画的东西，再跑 build。\n")
        return

    def dwidth(s):
        return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in s)

    def pad(s, w):
        return s + " " * max(w - dwidth(s), 0)

    head = [("id", 15), ("场景", 20), ("尺寸", 11), ("比例", 7), ("风格", 0)]
    sys.stdout.write("".join(pad(h, w) for h, w in head) + "\n")
    sys.stdout.write("-" * 76 + "\n")
    for p in items:
        sys.stdout.write(
            pad(p["id"], 15) + pad(p["scene"], 20) + pad(p["size"], 11) + pad(p["aspect"], 7) + p["style"] + "\n"
        )
    sys.stdout.write("\n看某个模板的完整提示词：presets --id xhs-cover\n")
    sys.stdout.write("内容由用户自己写，模板只给尺寸、比例和风格骨架。上面所有 size 两家协议都能过。\n")


def cmd_self_test(args):
    """全离线自检：不需要网络、不需要 Key，跑完必成功。"""
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        sys.stdout.write("[%s] %s%s\n" % ("PASS" if cond else "FAIL", name, ("  " + detail) if detail else ""))
        if not cond:
            ok = False

    # 1. size 解析
    check("size 解析 1024x1536", parse_size("1024x1536", "x") == (1024, 1536))
    check("size 解析 1024*1536", parse_size("1024*1536", "*") == (1024, 1536))
    check("size 解析 auto", parse_size("auto", "x") == (None, None))
    check("size 解析非法值", parse_size("1024*1536x", "x") == (None, None))

    # 2. 参数校验：openai 档位提示
    a = argparse.Namespace(proto="openai", model="gpt-image-2", size="1024x1536", n=1, image=None)
    p, n = validate(a)
    check("openai gpt-image-2 1024x1536 通过", p == [], str(p))

    # 3. 分隔符用错应当被拦下
    a = argparse.Namespace(proto="openai", model="qwen-image-3.0", size="1024*1536", n=1, image=None)
    p, _ = validate(a)
    check("qwen 走 openai 用星号会被拦", any("分隔符" in x for x in p), str(p))

    # 4. 像素上限
    a = argparse.Namespace(proto="dashscope", model="qwen-image-3.0", size="4096*4096", n=1, image=None)
    p, _ = validate(a)
    check("4096*4096 超上限被拦", any("上限" in x for x in p), str(p))

    # 5. 宽高比
    a = argparse.Namespace(proto="dashscope", model="qwen-image-3.0", size="2048*100", n=1, image=None)
    p, _ = validate(a)
    check("宽高比 20:1 被拦", any("宽高比" in x for x in p), str(p))

    # 6. 请求体构造：openai 文生图
    a = argparse.Namespace(proto="openai", model="gpt-image-2", prompt="一只橘猫", size="1024x1536", n=1,
                           response_format=None, image=None, negative_prompt=None, seed=None, watermark=False)
    b = build_body(a)
    check("openai 文生图字段", b == {"model": "gpt-image-2", "prompt": "一只橘猫", "size": "1024x1536", "n": 1}, str(b))

    # 7. 请求体构造：openai 兼容图生图用 image 字段
    a.image = ["http://x/a.png"]
    b = build_body(a)
    check("openai 图生图用 image 字段", b.get("image") == "http://x/a.png", str(b))

    # 8. 百炼同步：text + image 顺序
    a = argparse.Namespace(proto="dashscope", model="qwen-image-3.0", prompt="改成水彩", size="1024*1024", n=1,
                           image=["http://x/a.png"], negative_prompt=None, seed=None, watermark=False)
    b = build_body(a)
    content = b["input"]["messages"][0]["content"]
    check("百炼 content 里 image 在前 text 在后",
          content == [{"image": "http://x/a.png"}, {"text": "改成水彩"}], str(content))
    check("百炼 size 用星号", b.get("parameters", {}).get("size") == "1024*1024", str(b))

    # 9. 响应解析：四种形态都要能抓到图
    samples = {
        "openai b64": {"data": [{"b64_json": "AAAA", "url": ""}]},
        "openai url": {"data": [{"url": "https://x/a.png"}]},
        "百炼同步": {"output": {"choices": [{"message": {"content": [{"image": "https://x/a.png"}]}}]}},
        "百炼异步": {"output": {"task_status": "SUCCEEDED",
                                "choices": [{"message": {"content": [{"image": "https://x/b.png"}]}}]}},
    }
    for name, s in samples.items():
        got = iter_images(s)
        check("解析 %s" % name, len(got) >= 1, str(got))

    # 10. 预设尺寸必须全部能过校验，否则模板会给出非法参数
    for preset in PRESETS:
        a = argparse.Namespace(proto="dashscope", model="qwen-image-3.0",
                               size=preset["size"].replace("x", "*"), n=1, image=None)
        pr, _ = validate(a)
        check("预设 %s 尺寸合法" % preset["id"], pr == [], str(pr))

    # 11. 预设提示词必须给用户留位置，不能写死内容
    check("预设提示词都有占位符",
          all("【用户补充的内容】" in preset["prompt"] for preset in PRESETS))

    # 12. PNG 头读取（用内存里生成的最小 PNG，不落临时文件也能验）
    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8AAAwAB/wFbCwAAAABJRU5ErkJggg=="
    )
    tmp = Path(os.environ.get("TEMP", ".")) / "_image_api_selftest.png"
    tmp.write_bytes(png)
    r = image_size(tmp)
    check("读 PNG 头", r is not None and r[0] >= 1 and r[1] >= 1, str(r))
    try:
        tmp.unlink()
    except OSError:
        pass

    sys.stdout.write("\n%s\n" % ("自检全部通过。脚本无需网络与 Key 也能工作；联网的 probe/send/save 需要接口地址与 Key。" if ok else "有检查项未通过，修好再交付。"))
    raise SystemExit(0 if ok else 1)


# ---------------------------------------------------------------- CLI

def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="image_api.py",
        description="图片生成接口本地工具：离线可校验参数、构造请求、读图尺寸；联网可探测模型、发请求、存图。",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("self-test", help="离线自检，不需要网络与 Key")
    p.set_defaults(func=cmd_self_test)

    p = sub.add_parser("validate", help="校验参数（离线）")
    p.add_argument("--proto", required=True, choices=PROTOS)
    p.add_argument("--model", required=True)
    p.add_argument("--size")
    p.add_argument("--n", type=int)
    p.add_argument("--image", nargs="*", help="参考图，可多张")
    p.set_defaults(func=lambda a: _run_validate(a))

    p = sub.add_parser("build", help="构造请求体（离线，输出 JSON + curl）")
    p.add_argument("--proto", required=True, choices=PROTOS)
    p.add_argument("--model", required=True)
    p.add_argument("--prompt")
    p.add_argument("--size")
    p.add_argument("--n", type=int)
    p.add_argument("--image", nargs="*")
    p.add_argument("--negative-prompt")
    p.add_argument("--seed", type=int)
    p.add_argument("--watermark", action="store_true")
    p.add_argument("--response-format", choices=["url", "b64_json"])
    p.add_argument("--out", default="request.json")
    p.set_defaults(func=lambda a: _run_build(a))

    p = sub.add_parser("presets", help="列出常用尺寸模板（离线）")
    p.add_argument("--id", help="看单个模板的完整提示词")
    p.add_argument("--scene", help="按场景过滤，如 公众号 / 小红书 / 海报")
    p.add_argument("--json", action="store_true", help="输出 JSON")
    p.set_defaults(func=cmd_presets)

    p = sub.add_parser("init", help="保存接口地址与 Key（之后不用每次传）")
    p.add_argument("--base-url", help="OpenAI 兼容接口一般形如 https://your-host/v1")
    p.add_argument("--key", help="API Key；不给就交互式输入")
    p.add_argument("--show", action="store_true", help="查看当前配置（Key 打码）")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("probe", help="GET {base}/models，列出可用模型")
    p.add_argument("--base-url", help="不给就用 init 保存的地址或环境变量")
    p.add_argument("--key", help="不给就用 init 保存的 Key 或环境变量")
    p.set_defaults(func=cmd_probe)

    p = sub.add_parser("send", help="发送 request.json 并保存原始响应")
    p.add_argument("--base-url", help="不给就用 init 保存的地址或环境变量")
    p.add_argument("--key", help="不给就用 init 保存的 Key 或环境变量")
    p.add_argument("--request", required=True)
    p.add_argument("--proto", required=True, choices=PROTOS)
    p.add_argument("--out", default="response.json")
    p.add_argument("--timeout", type=int, default=480)
    p.set_defaults(func=cmd_send)

    p = sub.add_parser("save", help="解析响应，落盘图片并核对尺寸")
    p.add_argument("--response", required=True)
    p.add_argument("--out-dir", default="out")
    p.add_argument("--expect-size", help="请求时的 size，用于比对实际输出")
    p.set_defaults(func=cmd_save)

    p = sub.add_parser("size", help="读图片文件真实宽高")
    p.add_argument("files", nargs="+")
    p.set_defaults(func=cmd_size)

    args = ap.parse_args(argv)

    # 需要联网的两个命令：参数缺了就回落到环境变量和配置文件，实在没有才报错
    if args.cmd in ("probe", "send"):
        args.base_url = resolve_base_url(args.base_url)
        args.key = resolve_key(args.key)
        if not args.base_url:
            die("缺接口地址：用 --base-url 传入，或先跑 %s init 保存一次" % Path(sys.argv[0]).name)
        if not args.key:
            die("缺 Key：用 --key 传入，或先跑 %s init 保存一次" % Path(sys.argv[0]).name)

    args.func(args)


def _run_validate(a):
    problems, notes = validate(a)
    out({"proto": a.proto, "model": a.model, "size": a.size, "n": a.n,
         "problems": problems, "notes": notes, "verdict": "通过" if not problems else "有问题"})
    if problems:
        raise SystemExit(1)


def _run_build(a):
    problems, notes = validate(a)
    for x in notes:
        sys.stdout.write("note: %s\n" % x)
    if problems:
        for x in problems:
            sys.stdout.write("problem: %s\n" % x)
        die("参数有问题，先修再构造请求")
    body = build_body(a)
    Path(a.out).write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
    sys.stdout.write("请求体已写 %s\n\n等价 curl（Key 用环境变量，不落明文）：\n%s\n" % (a.out, to_curl(a, body)))


if __name__ == "__main__":
    main()
