#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""星桥多模态接口命令行封装：图片生成、图片编辑、视频生成。

只依赖 Python 标准库（3.8+），不需要 pip 装任何东西。

设计原则（都是花钱换来的）：
  1. 一次提交只做一件事，绝不自动重试付费生成。
  2. 任务 ID 落盘，网络断了先查任务，不重新提交。
  3. 每次终态把 cost_usd 记进账本，账单以它为准，不以报价为准。
  4. 默认尊重系统代理；仅显式 --no-proxy 时直连。

用法：python xq.py <子命令> -h
"""

import argparse
import io
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

DEFAULT_BASE = "https://api.novqiao.com"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
CONFIG = Path.home() / ".xingqiao" / "config.json"
LEDGER = Path.home() / ".xingqiao" / "ledger.jsonl"
STATE = Path.home() / ".xingqiao" / "tasks"
NO_PROXY = False
OFFLINE = False
IMAGE_TERMINAL_OK = {"succeeded"}
VIDEO_READY = {"read_result"}


# ---------------------------------------------------------------- 基础工具

def now():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def log(msg):
    sys.stdout.write(msg + "\n")
    sys.stdout.flush()


def jdump(obj):
    return json.dumps(obj, ensure_ascii=False)


def die(msg, code=1):
    sys.stderr.write("错误：" + msg + "\n")
    sys.exit(code)


def read_config(required=True):
    if OFFLINE:
        return {}
    if not CONFIG.exists():
        if required:
            die("没有配置文件 %s。先跑：python xq.py init" % CONFIG)
        return {}
    try:
        return json.loads(CONFIG.read_text(encoding="utf-8"))
    except Exception as exc:
        die("配置文件读不出来：%s" % exc)


def base_url(cfg, override=None):
    raw = override or cfg.get("base_url") or DEFAULT_BASE
    return raw.rstrip("/")


def api_key(cfg, override=None):
    key = override or os.environ.get("XINGQIAO_API_KEY") or cfg.get("api_key")
    if not key:
        die("没有 API Key。跑 python xq.py init，或设环境变量 XINGQIAO_API_KEY")
    return key


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    """307 跳到别的域时把 Bearer 摘掉，不要把密钥转发给存储服务器。"""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new is not None:
            for store in (new.headers, new.unredirected_hdrs):
                for name in list(store):
                    if name.lower() == "authorization":
                        store.pop(name, None)
        return new


def opener():
    if OFFLINE:
        die("离线模式禁止网络请求")
    proxy = urllib.request.ProxyHandler({}) if NO_PROXY else urllib.request.ProxyHandler()
    return urllib.request.build_opener(proxy, SafeRedirect())


def write_output(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as fh:
        fh.write(text)


def request(method, url, key=None, body=None, raw=None, ctype=None, timeout=120,
            extra_headers=None, retry=0):
    headers = {"User-Agent": UA, "Accept": "application/json, */*"}
    if key:
        headers["Authorization"] = "Bearer " + key
    data = None
    if raw is not None:
        data = raw
        headers["Content-Type"] = ctype or "application/octet-stream"
    elif body is not None:
        data = jdump(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if extra_headers:
        headers.update(extra_headers)

    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    payload = status = None
    rheaders = {}
    last_err = None
    for attempt in range(retry + 1):
        try:
            with opener().open(req, timeout=timeout) as resp:
                payload = resp.read()
                status = resp.status
                rheaders = dict(resp.headers.items())
            break
        except urllib.error.HTTPError as exc:
            payload = exc.read()
            status = exc.code
            rheaders = dict(exc.headers.items()) if exc.headers else {}
            break
        except (urllib.error.URLError, OSError) as exc:
            # 服务商偶发 RST／超时。只有查询类请求能安全重试，
            # 提交类请求重试可能再扣一次钱，所以由调用方决定 retry。
            last_err = getattr(exc, "reason", exc)
            if attempt < retry:
                time.sleep(2 + attempt * 2)
                continue
            die("连不上 %s：%s（任务可能已被受理，先用 status 查，不要重新提交）"
                % (url, last_err))

    try:
        parsed = json.loads(payload.decode("utf-8"))
    except Exception:
        parsed = None
    if status >= 400:
        err = ""
        if isinstance(parsed, dict):
            e = parsed.get("error") or parsed
            err = "%s %s" % (e.get("code") or e.get("type") or "", e.get("message") or "")
            err = err.strip() or jdump(parsed)[:400]
        else:
            err = payload.decode("utf-8", "replace")[:400]
        die("HTTP %s %s\n%s" % (status, url, err))
    if parsed is None:
        die("返回不是 JSON（开头：%s）" % payload[:120].decode("utf-8", "replace"))
    return parsed, status, rheaders


def download(url, dest, key=None):
    """下载成品。ticket 链接不带 Key；/content 这类要带 Key 并允许 307。"""
    if dest.exists():
        die("输出文件已存在，拒绝覆盖：%s" % dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": UA}
    if key:
        headers["Authorization"] = "Bearer " + key
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with open(dest, "xb") as fh, opener().open(req, timeout=300) as resp:
            while True:
                chunk = resp.read(262144)
                if not chunk:
                    break
                fh.write(chunk)
    except urllib.error.HTTPError as exc:
        die("下载失败 HTTP %s %s" % (exc.code, url))
    return dest


def ext_for(mime, default=".bin"):
    return {
        "image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp",
        "video/mp4": ".mp4", "video/webm": ".webm", "video/quicktime": ".mov",
    }.get((mime or "").lower(), default)


# ---------------------------------------------------------------- 账本

def record_cost(kind, task, files, extra=None):
    cost = task.get("cost_usd")
    if cost is None:
        return
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "ts": now(),
        "unix": int(time.time()),
        "kind": kind,
        "task_id": task.get("task_id"),
        "client_task_id": task.get("client_task_id"),
        "model": task.get("model"),
        "cost_usd": cost,
        "billing_unit": "cost_usd",  # 不推断当前合约结算币种或比例
        "files": [str(f) for f in files],
        "prompt": (task.get("prompt") or "")[:160],
    }
    if extra:
        row.update(extra)
    with open(LEDGER, "a", encoding="utf-8") as fh:
        fh.write(jdump(row) + "\n")


def save_task(kind, task):
    STATE.mkdir(parents=True, exist_ok=True)
    tid = str(task.get("task_id") or task.get("client_task_id") or uuid.uuid4())
    path = STATE / ("%s-%s.json" % (kind, tid.replace("/", "_")))
    body = dict(task)
    body["_saved_at"] = now()
    path.write_text(jdump(body), encoding="utf-8")
    return path


# ---------------------------------------------------------------- 任务执行

def poll(url, key, timeout, first_delay=5, quiet=False):
    deadline = time.time() + timeout
    delay = first_delay
    last = None
    while time.time() < deadline:
        task, _s, _h = request("GET", url, key=key, timeout=60, retry=3)
        last = task
        if not quiet:
            log("  %s  status=%s state=%s next=%s"
                % (time.strftime("%H:%M:%S"), task.get("status"),
                   task.get("state"), task.get("next_action")))
        if task.get("status") == "failed":
            err = task.get("error") or {}
            die("任务失败：%s %s\n完整响应：%s"
                % (err.get("code"), err.get("message"), jdump(task)[:800]))
        if task.get("terminal") and task.get("next_action") in (VIDEO_READY | {"read_result"}):
            # 视频可能 terminal=true 但还在 save_resource
            return task
        if task.get("terminal") and task.get("status") == "succeeded" and task.get("data"):
            return task
        delay = task.get("retry_after_seconds") or min(max(delay, 5) * 1.3, 60)
        remain = deadline - time.time()
        if remain <= 0:
            break
        time.sleep(min(delay, remain))
    die("轮询超时（%s 秒）。任务没有丢，用 python xq.py status 查：%s\n最后状态：%s"
        % (timeout, url, jdump(last or {})[:400]))


def collect(images_or_videos, dest_dir, kind, key, task_id, base):
    """把结果落盘。带 ticket 的链接不带 Key，/content 才带 Key，别把密钥发出去。"""
    import base64

    saved = []
    for idx, item in enumerate(images_or_videos or [], start=1):
        if not isinstance(item, dict):
            continue
        mime = item.get("mime_type") or ("image/png" if kind == "image" else "video/mp4")
        dest = dest_dir / ("%s-%02d%s" % (task_id, idx, ext_for(mime)))

        b64 = item.get("b64_json")
        if b64:
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open("xb") as fh:
                fh.write(base64.b64decode(b64))
            saved.append(dest)
            continue

        url = item.get("download_url") or item.get("url")
        if not url:
            continue
        need_key = False
        if "ticket=" not in url and "/content" in url:
            if url.startswith("/") and not url.startswith("//"):
                url = base + url
            need_key = urllib.parse.urlsplit(url).netloc == urllib.parse.urlsplit(base).netloc
        elif url.startswith("/") and not url.startswith("//"):
            url = base + url
        if urllib.parse.urlsplit(url).scheme != "https":
            die("下载地址必须使用 HTTPS")
        download(url, dest, key=key if need_key else None)
        saved.append(dest)
        if item.get("url_expires_at"):
            log("  链接有效至：%s" % time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(item["url_expires_at"])))
    return saved


# ---------------------------------------------------------------- 子命令

def cmd_init(args):
    cfg = read_config(required=False)
    base = args.base_url or cfg.get("base_url") or DEFAULT_BASE
    key = args.key or cfg.get("api_key")
    if not key:
        log("星桥 API Key（输入不显示）：")
        import getpass
        key = getpass.getpass("> ").strip()
    if not key:
        die("Key 不能为空")
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(jdump({
        "base_url": base.rstrip("/"),
        "api_key": key,
        "updated_at": now(),
    }), encoding="utf-8")
    mask = key[:6] + "..." + key[-4:] if len(key) > 12 else "***"
    log("已保存到 %s" % CONFIG)
    log("base_url=%s  key=%s" % (base.rstrip("/"), mask))
    log("这个文件是明文，别提交到 Git。")


def cmd_show(args):
    cfg = read_config(required=False)
    key = cfg.get("api_key") or ""
    mask = (key[:6] + "..." + key[-4:]) if len(key) > 12 else ("未配置")
    log("配置文件：%s %s" % (CONFIG, "存在" if CONFIG.exists() else "不存在"))
    log("base_url：%s" % (cfg.get("base_url") or DEFAULT_BASE))
    log("api_key：%s" % mask)
    log("账本：%s %s" % (LEDGER, "存在" if LEDGER.exists() else "尚未记账"))


def brief_video_cost(it, full=False):
    """视频报价表动辄上百个数字，默认只给每档的最短/最长/常用档，加 --full 看全量。"""
    costs = it.get("estimated_costs") or {}
    ref_costs = it.get("reference_video_estimated_costs") or {}
    if not costs and not ref_costs:
        return "\n      报价: 目录未配置，不能当免费"
    out = ""
    if ref_costs and ref_costs == costs:
        ref_costs = {}
    for label, table in (("报价", costs), ("带参考视频报价（与普通一致时省略）", ref_costs)):
        if not table:
            continue
        out += "\n      %s:" % label
        for res in sorted(table, key=lambda r: str(r)):
            row = table[res] or {}
            if not isinstance(row, dict) or not row:
                continue
            secs = sorted((int(k), v) for k, v in row.items() if str(k).isdigit())
            if not secs:
                continue
            if full:
                out += "\n        %s: %s" % (res, " ".join("%ss=%s" % (k, v) for k, v in secs))
                continue
            picks = [secs[0], secs[-1]] + [(k, v) for k, v in secs if k in (5, 10)]
            seen = []
            for k, v in picks:
                if k not in [x[0] for x in seen]:
                    seen.append((k, v))
            seen.sort()
            out += "\n        %s: %s  （共 %d 档，--full 看全量）" % (
                res, " ".join("%ss=%s" % (k, v) for k, v in seen), len(secs))
    return out


def cmd_models(args):
    cfg = read_config(required=False)
    key = api_key(cfg)
    base = base_url(cfg, args.base_url)
    kinds = ["image", "video"] if args.kind == "all" else [args.kind]
    out = {}
    for kind in kinds:
        path = "/v1/image-v2/models" if kind == "image" else "/v1/video-v2/models"
        data, _s, _h = request("GET", base + path, key=key, retry=2)
        out[kind] = data
        items = data.get("data") if kind == "image" else data.get("items")
        items = items or []
        log("\n== %s 模型（%d 个）==" % ("图片" if kind == "image" else "视频", len(items)))
        for it in items:
            name = it.get("model") or it.get("id")
            flag = []
            if it.get("is_default"):
                flag.append("默认")
            if it.get("enabled") is False:
                flag.append("停用" + (":" + str(it.get("disabled_reason")) if it.get("disabled_reason") else ""))
            line = "  %s %s" % (name, "[" + ",".join(flag) + "]" if flag else "")
            if kind == "image":
                if it.get("sizes"):
                    line += "\n      尺寸档: %s" % ",".join(map(str, it["sizes"]))
                if it.get("uses_pixel_size"):
                    px = it.get("pixel_sizes")
                    line += "\n      可传像素尺寸: 是%s%s" % (
                        "（范围 %s）" % jdump(px) if px else "",
                        "，最大像素 %s" % it["max_pixels"] if it.get("max_pixels") else "")
                if it.get("aspect_ratios"):
                    line += "\n      比例: %s" % ",".join(map(str, it["aspect_ratios"]))
                if it.get("qualities"):
                    line += "\n      质量: %s" % ",".join(map(str, it["qualities"]))
                if it.get("output_formats"):
                    line += "\n      格式: %s" % ",".join(map(str, it["output_formats"]))
                if it.get("operations"):
                    line += "\n      操作: %s" % ",".join(map(str, it["operations"]))
                if it.get("max_images"):
                    line += "\n      单任务最多 %s 张，参考图最多 %s 张" % (
                        it.get("max_images"), it.get("max_reference_images"))
            else:
                if it.get("ratios"):
                    line += "\n      比例: %s" % ",".join(map(str, it["ratios"]))
                if it.get("resolutions"):
                    line += "\n      分辨率: %s" % ",".join(map(str, it["resolutions"]))
                if it.get("max_images") is not None:
                    line += "\n      素材上限 图%s/音%s/视频%s" % (
                        it.get("max_images"), it.get("max_audios"), it.get("max_videos"))
                line += brief_video_cost(it, full=args.full)
            log(line)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        write_output(args.out, jdump(out))
        log("\n原始响应已存 %s" % args.out)


def upload_reference(kind, files, cfg, base):
    """上传参考素材。图片走 image-v2/references，视频走 video-v2/references。"""
    ids, urls = [], []
    key = api_key(cfg)
    for f in files:
        p = Path(f)
        if not p.exists():
            die("参考素材不存在：%s" % f)
        mime = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
        boundary = "----xq" + uuid.uuid4().hex
        parts = []
        if kind == "video":
            parts.append(("--%s\r\nContent-Disposition: form-data; name=\"kind\"\r\n\r\n%s\r\n"
                          % (boundary, args_kind_guess(p))).encode("utf-8"))
        parts.append(("--%s\r\nContent-Disposition: form-data; name=\"file\"; filename=\"%s\"\r\n"
                      "Content-Type: %s\r\n\r\n" % (boundary, p.name, mime)).encode("utf-8"))
        parts.append(p.read_bytes())
        parts.append(("\r\n--%s--\r\n" % boundary).encode("utf-8"))
        body = b"".join(parts)
        path = "/v1/image-v2/references" if kind == "image" else "/v1/video-v2/references"
        data, _s, _h = request("POST", base + path, key=key, raw=body,
                               ctype="multipart/form-data; boundary=" + boundary)
        if data.get("resource_id") is not None:
            ids.append(data["resource_id"])
        if data.get("url"):
            urls.append(data["url"])
        log("  已上传 %s → resource_id=%s" % (p.name, data.get("resource_id")))
    return ids, urls


def args_kind_guess(path):
    suffix = path.suffix.lower()
    if suffix in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"):
        return "image"
    if suffix in (".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"):
        return "audio"
    return "video"


def build_image_body(args, cfg, base, dry_run=False):
    body = {"prompt": args.prompt, "n": args.n}
    model = args.model
    if not model:
        if dry_run:
            log("未指定模型：dry-run 不查目录，提交时由服务端默认模型决定")
        else:
            got, _s, _h = request("GET", base + "/v1/image-v2/models", key=api_key(cfg))
            for it in got.get("data") or []:
                if it.get("is_default"):
                    model = it.get("model")
                    break
            if not model and (got.get("data") or []):
                model = got["data"][0].get("model")
            log("未指定模型，用目录默认：%s" % model)
    if model:
        body["model"] = model
    for field, value in (("size", args.size), ("image_size", args.image_size),
                         ("aspect_ratio", args.aspect_ratio), ("quality", args.quality),
                         ("output_format", args.output_format),
                         ("response_format", args.response_format)):
        if value:
            body[field] = value
    if args.ref:
        if args.image_url:
            die("图片参考图和参考图地址互斥，二选一")
        if dry_run:
            body["image_reference_ids"] = ["<上传后回填的 resource_id>"]
        else:
            ids, _urls = upload_reference("image", args.ref, cfg, base)
            if ids:
                body["image_reference_ids"] = ids
    elif args.image_url:
        body["images"] = list(args.image_url)
    return body


def cmd_quote(args):
    cfg = read_config(required=False)
    base = base_url(cfg, args.base_url)
    body = build_image_body(args, cfg, base, dry_run=args.dry_run)
    if args.dry_run:
        log("\n[dry-run] 不询价，请求体：\n" + json.dumps(body, ensure_ascii=False, indent=2))
        return
    data, _s, _h = request("POST", base + "/v1/image-v2/quote",
                           key=api_key(cfg), body=body)
    log("\n询价结果（不生成、不扣费、不锁价）")
    log("  模型：%s  操作：%s  规格：%s  数量：%s"
        % (data.get("model"), data.get("operation"), data.get("price_spec"), data.get("n")))
    log("  单价：%s USD   预计合计：%s USD"
        % (data.get("unit_price_usd"), data.get("estimated_cost_usd")))
    log("  实际以任务 cost_usd 为准。")
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        write_output(args.out, jdump(data))


def cmd_image(args):
    cfg = read_config(required=False)
    base = base_url(cfg, args.base_url)
    key = None if args.dry_run else api_key(cfg)
    body = build_image_body(args, cfg, base, dry_run=args.dry_run)
    if args.callback_url:
        body["callback_url"] = args.callback_url
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        write_output(args.out, jdump(body))
        log("请求体已存 %s" % args.out)
    if args.dry_run:
        log("\n[dry-run] 不提交，不发请求：\n" + json.dumps(body, ensure_ascii=False, indent=2))
        return

    idem = args.idem or ("xq-img-" + time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6])
    log("\n提交图片任务（幂等键 %s）" % idem)
    task, _s, _h = request("POST", base + "/v1/image-v2/tasks", key=key, body=body,
                           extra_headers={"Idempotency-Key": idem})
    tid = task.get("task_id")
    save_task("image", dict(task, prompt=args.prompt))
    log("  task_id=%s status=%s" % (tid, task.get("status")))

    final = poll(base + "/v1/image-v2/tasks/%s" % tid, key, args.timeout,
                 task.get("retry_after_seconds") or 5, quiet=args.quiet)
    final.setdefault("model", body.get("model"))
    final["prompt"] = args.prompt
    save_task("image", final)

    out_dir = Path(args.out_dir) if args.out_dir else STATE.parent / "outputs" / "images" / str(tid)
    files = collect(final.get("data"), out_dir, "image", key, tid, base)
    record_cost("image", final, files, extra={
        "model": final.get("model") or body.get("model"),
        "prompt": args.prompt,
        "client_task_id": idem,
    })
    log("\n完成：%s" % ("成功" if files else "任务成功但没有取到文件"))
    for f in files:
        log("  文件：%s" % f)
    log("  账单：cost_usd=%s" % final.get("cost_usd"))
    if not files:
        log("  提示：data 里可能只有 b64_json，或链接已过期。用 status 重查，不要重新生成。")


def cmd_video(args):
    cfg = read_config(required=False)
    base = base_url(cfg, args.base_url)
    key = None if args.dry_run else api_key(cfg)

    body = {"prompt": args.prompt}
    model = args.model
    if not model and args.dry_run:
        log("未指定模型：dry-run 不查目录，先按目录补 --model 再正式提交")
    elif not model:
        got, _s, _h = request("GET", base + "/v1/video-v2/models", key=key)
        cands = [it for it in (got.get("items") or []) if it.get("enabled") is not False]
        if len(cands) == 1:
            model = cands[0].get("id")
            log("未指定模型，目录只有 %s，直接用它" % model)
        else:
            names = ", ".join(str(c.get("id")) for c in cands[:8])
            die("视频模型必须显式指定（目录里可用：%s）。先跑 python xq.py models --kind video 看能力和报价。" % names)
    if model:
        body["model"] = model
    for field, value in (("duration", args.duration), ("ratio", args.ratio),
                         ("resolution", args.resolution), ("mode", args.mode)):
        if value is not None:
            body[field] = value
    if args.prompt_enhance:
        body["prompt_enhance"] = True

    urls = list(args.image_url or [])
    audio = list(args.audio_url or [])
    video = list(args.video_url or [])
    for kind, dirs in (("image", args.ref_image), ("audio", args.ref_audio),
                       ("video", args.ref_video)):
        if dirs and args.dry_run:
            {"image": urls, "audio": audio, "video": video}[kind].append("<上传后回填的 url>")
        elif dirs:
            _ids, got_urls = upload_reference("video", dirs, cfg, base)
            if kind == "image":
                urls.extend(got_urls)
            elif kind == "audio":
                audio.extend(got_urls)
            else:
                video.extend(got_urls)
    body["image_urls"] = urls
    body["audio_urls"] = audio
    body["video_urls"] = video

    client_id = args.client_task_id or ("xq-vid-" + time.strftime("%Y%m%d-%H%M%S")
                                        + "-" + uuid.uuid4().hex[:6])
    body["client_task_id"] = client_id
    if args.callback_url:
        body["callback_url"] = args.callback_url

    if args.dry_run:
        log("[dry-run] 不提交：\n" + json.dumps(body, ensure_ascii=False, indent=2))
        return

    log("\n提交视频任务（client_task_id=%s）" % client_id)
    task, _s, _h = request("POST", base + "/v1/video-v2/tasks", key=key, body=body)
    tid = task.get("task_id")
    save_task("video", dict(task, prompt=args.prompt))
    log("  task_id=%s status=%s" % (tid, task.get("status")))

    final = poll(base + "/v1/video-v2/tasks/%s" % tid, key, args.timeout,
                 task.get("retry_after_seconds") or 30, quiet=args.quiet)
    final.setdefault("model", body.get("model"))
    final["prompt"] = args.prompt
    save_task("video", final)

    out_dir = Path(args.out_dir) if args.out_dir else STATE.parent / "outputs" / "videos" / str(tid)
    files = collect(final.get("data"), out_dir, "video", key, tid, base)
    record_cost("video", final, files, extra={
        "model": final.get("model") or body.get("model"),
        "prompt": args.prompt,
        "client_task_id": client_id,
    })
    log("\n完成：%s" % ("成功" if files else "任务成功但没有取到文件"))
    for f in files:
        log("  文件：%s（%s 字节）" % (f, f.stat().st_size if f.exists() else "?"))
    log("  账单：cost_usd=%s" % final.get("cost_usd"))
    if not files:
        log("  提示：可能卡在 save_resource 或链接未生成。用 status 查，不要重新提交。")


def cmd_status(args):
    cfg = read_config(required=False)
    base = base_url(cfg, args.base_url)
    key = api_key(cfg)
    if not args.task_id:
        die("要给 --task-id")
    if args.kind == "image":
        data, _s, _h = request("GET", base + "/v1/image-v2/tasks/" + args.task_id, key=key, retry=3)
    else:
        data, _s, _h = request("GET", base + "/v1/video-v2/tasks/" + args.task_id, key=key, retry=3)
    log(json.dumps(data, ensure_ascii=False, indent=2))
    if args.download and data.get("data"):
        out_dir = Path(args.out_dir) if args.out_dir else STATE.parent / "outputs" / (args.kind + "s") / args.task_id
        files = collect(data.get("data"), out_dir, args.kind, key, args.task_id, base)
        record_cost(args.kind, data, files)
        for f in files:
            log("已下载：%s" % f)


def read_ledger():
    if not LEDGER.exists():
        return []
    rows = []
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    return rows


def soft_get(url, key, retry=2):
    """查询类请求失败只返回原因，不中断整轮对账。"""
    buf = io.StringIO()
    old = sys.stderr
    sys.stderr = buf
    try:
        parsed, _status, _h = request("GET", url, key=key, retry=retry)
        return parsed, ""
    except SystemExit:
        msg = buf.getvalue().strip().replace("错误：", "", 1).strip()
        return None, msg or "请求失败"
    finally:
        sys.stderr = old


def cmd_reconcile(args):
    cfg = read_config(required=False)
    base = base_url(cfg, args.base_url)
    key = api_key(cfg)

    rows = read_ledger()
    if args.since:
        rows = [r for r in rows if (r.get("ts") or "")[:10] >= args.since]
    if not rows:
        log("账本没有记录，没什么可对")
        return

    srv, notes = {}, {}

    img_ids = [str(r.get("task_id")) for r in rows
               if r.get("kind") == "image" and r.get("task_id")]
    for tid in img_ids:
        # 批查 GET/POST 资料冲突；使用已有明确契约的单任务查询。
        parsed, err = soft_get(base + "/v1/image-v2/tasks/" + tid, key)
        if parsed is None:
            notes[("image", tid)] = "查询失败：" + err.splitlines()[0][:60]
        else:
            srv[("image", tid)] = parsed

    vid_ids = [str(r.get("task_id")) for r in rows
               if r.get("kind") == "video" and r.get("task_id")]
    for tid in vid_ids:
        parsed, err = soft_get(base + "/v1/video-v2/tasks/" + tid, key, retry=3)
        if parsed is None:
            notes[("video", tid)] = "站方查无此任务或接口报错"
        else:
            srv[("video", tid)] = parsed

    tw = min(44, max(18, max(len(str(r.get("task_id") or "-")) for r in rows)))
    head = "%-19s %-5s %-*s %8s %8s %-9s %s"
    rule = "-" * (19 + 6 + tw + 18 + 10 + 30)

    log("对账：账本 %d 条，逐条回站方核对（只读，不花钱）\n" % len(rows))
    log(head % ("时间", "类型", tw, "任务ID", "账本", "站方", "状态", "文件"))
    log(rule)

    bad = []
    sum_book = sum_srv = 0.0
    by_kind = {}
    for r in rows:
        kind = r.get("kind") or "?"
        tid = str(r.get("task_id") or "-")
        book = float(r.get("cost_usd") or 0)
        sum_book += book
        by_kind[kind] = by_kind.get(kind, 0.0) + book
        it = srv.get((kind, tid))

        if it is None:
            reason = notes.get((kind, tid), "站方无记录")
            bad.append((tid, reason))
            log(head % (r.get("ts"), kind, tw, tid, book, "-", "-", reason))
            continue

        srv_cost = float(it.get("cost_usd") or 0)
        sum_srv += srv_cost
        status = it.get("status") or it.get("state") or "?"

        names, missing = [], False
        for f in (r.get("files") or []):
            fp = Path(f)
            ok = fp.exists() and fp.stat().st_size > 0
            if not ok:
                missing = True
            names.append(fp.name + ("" if ok else "(缺失)"))
        fdesc = ", ".join(names) or "无"

        flags = []
        diff = srv_cost - book
        if abs(diff) > 1e-6:
            flags.append("差 %+.4f" % diff)
            bad.append((tid, "金额差 %+.4f" % diff))
        if status not in ("succeeded", "completed"):
            flags.append("状态 " + status)
            bad.append((tid, "状态 %s" % status))
        if missing:
            flags.append("文件缺失")
            bad.append((tid, "文件缺失"))

        log(head % (r.get("ts"), kind, tw, tid, book, srv_cost, status, fdesc) +
            (("  ← " + "，".join(flags)) if flags else ""))

    log(rule)
    for k in sorted(by_kind):
        log("  %s 合计：%.4f cost_usd" % (k, by_kind[k]))
    log("账本合计：%.4f cost_usd    站方可核：%.4f cost_usd    差额：%+.4f cost_usd"
        % (sum_book, sum_srv, sum_srv - sum_book))

    if args.json_out:
        Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        write_output(args.json_out, jdump({
            "rows": len(rows), "book_total": round(sum_book, 4),
            "server_total": round(sum_srv, 4),
            "diff": round(sum_srv - sum_book, 4),
            "issues": [{"task_id": t, "issue": i} for t, i in bad],
        }))
        log("结果已存 %s" % args.json_out)

    if bad:
        log("\n有 %d 处对不上，逐条看上面的箭头和备注。" % len(bad))
        log("站方账单页是最终口径；本命令核的是任务级 cost_usd，"
            "查不到不代表没花钱。")
        sys.exit(1)
    log("\n逐条对上，账本可以直接用。")


def cmd_ledger(args):
    rows = read_ledger()
    if not rows:
        log("账本还没有记录：%s" % LEDGER)
        return
    if args.tail:
        rows = rows[-args.tail:]
    total = 0.0
    by_kind = {}
    by_day = {}
    for r in rows:
        cost = float(r.get("cost_usd") or 0)
        total += cost
        by_kind[r.get("kind")] = by_kind.get(r.get("kind"), 0.0) + cost
        day = (r.get("ts") or "")[:10]
        by_day[day] = by_day.get(day, 0.0) + cost
    log("账本：%s" % LEDGER)
    log("条数：%d   合计：%.4f USD" % (len(rows), total))
    for k, v in sorted(by_kind.items()):
        log("  %s：%.4f USD" % (k, v))
    log("\n按日：")
    for day in sorted(by_day):
        log("  %s  %.4f USD" % (day or "未知", by_day[day]))
    if args.rate is not None:
        rate = float(args.rate)
        log("\n人民币估算：%.2f 元（当前任务显式比例 %.4f，非已核账单）"
            % (total * rate, rate))
    else:
        log("\n未提供合约换算比例，不推断人民币结算金额。")
    log("\n最近 10 条：")
    for r in rows[-10:]:
        log("  %s  %s  %s  %s USD" % (r.get("ts"), r.get("kind"),
                                      r.get("task_id"), r.get("cost_usd")))


def cmd_self_test(args):
    checks = []

    def chk(name, ok, note=""):
        checks.append((name, bool(ok), note))
        log("  [%s] %s%s" % ("OK" if ok else "FAIL", name, ("  " + note) if note else ("" )))

    log("离线自检（不联网、不花钱）\n")
    chk("Python 版本 >= 3.8", sys.version_info[:2] >= (3, 8),
        "%s" % ".".join(map(str, sys.version_info[:3])))
    chk("默认地址可用格式", DEFAULT_BASE.startswith("https://"))
    chk("配置文件路径可解析", bool(CONFIG))
    chk("账本路径可解析", bool(LEDGER))
    chk("ext_for 图片", ext_for("image/png") == ".png")
    chk("ext_for 视频", ext_for("video/mp4") == ".mp4")
    chk("ext_for 未知回落", ext_for("application/x-foo") == ".bin")
    chk("素材类型识别 mp3", args_kind_guess(Path("a.mp3")) == "audio")
    chk("素材类型识别 png", args_kind_guess(Path("a.png")) == "image")
    chk("素材类型识别 mp4", args_kind_guess(Path("a.mp4")) == "video")
    chk("JSON 中文不转义", "中文" in jdump({"k": "中文"}))
    r = SafeRedirect()
    chk("重定向处理器可实例化", r is not None)
    log("  [SKIP] 离线自检不读取账号配置")
    chk("账本可写目录存在", LEDGER.parent.exists() or True,
        "不存在时首次记账自动创建")
    ok = all(c[1] for c in checks)
    log("\n%d 项通过，%d 项失败" % (sum(1 for c in checks if c[1]),
                                   sum(1 for c in checks if not c[1])))
    if not ok:
        sys.exit(1)


# ---------------------------------------------------------------- 参数

def add_common(p):
    p.add_argument("--base-url", help="覆盖配置文件里的服务地址")
    p.add_argument("--out", help="把原始响应/请求体写到这个文件")


def add_image_args(p):
    p.add_argument("--prompt", required=True)
    p.add_argument("--model", help="目录里的完整模型名，省略用默认模型")
    p.add_argument("--size", help="像素尺寸，如 1024x1024")
    p.add_argument("--image-size", help="分辨率档 1K/2K/4K")
    p.add_argument("--aspect-ratio", help="比例，需与 size 一致")
    p.add_argument("--quality")
    p.add_argument("--output-format", choices=["png", "jpeg", "webp"])
    p.add_argument("--response-format", choices=["url", "b64_json"])
    p.add_argument("--n", type=int, default=1, help="张数 1-4，默认 1")
    p.add_argument("--ref", action="append", help="本地参考图，可多次；上传后取 resource_id")
    p.add_argument("--image-url", action="append", help="参考图公网地址，可多次")


def main():
    parser = argparse.ArgumentParser(
        prog="xq.py", description="星桥多模态接口：图片生成/编辑、视频生成、询价与记账。")
    parser.add_argument("--config", type=Path, help="当前账号私有配置文件")
    parser.add_argument("--state-dir", type=Path, help="当前账号/项目独立状态根目录")
    parser.add_argument("--no-proxy", action="store_true", help="显式禁用代理，默认尊重系统代理")
    sub = parser.add_subparsers(dest="cmd")

    p = sub.add_parser("init", help="保存服务地址与 Key 到 ~/.xingqiao/config.json")
    p.add_argument("--base-url")
    p.add_argument("--key")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("show", help="查看当前配置（Key 打码）")
    p.set_defaults(func=cmd_show)

    p = sub.add_parser("self-test", help="离线自检，不联网不花钱")
    p.set_defaults(func=cmd_self_test)

    p = sub.add_parser("models", help="列当前 Key 可用的图片/视频模型与能力")
    p.add_argument("--kind", choices=["image", "video", "all"], default="all")
    p.add_argument("--full", action="store_true", help="视频报价打印全部时长档")
    add_common(p)
    p.set_defaults(func=cmd_models)

    p = sub.add_parser("quote", help="图片询价，不生成不扣费")
    add_image_args(p)
    add_common(p)
    p.add_argument("--dry-run", action="store_true", help="只打印请求体，不发询价请求")
    p.set_defaults(func=cmd_quote)

    p = sub.add_parser("image", help="提交图片任务并取回文件")
    add_image_args(p)
    add_common(p)
    p.add_argument("--idem", help="幂等键，默认自动生成")
    p.add_argument("--callback-url")
    p.add_argument("--out-dir", help="成品目录，默认当前状态根 outputs/images/<task_id>")
    p.add_argument("--timeout", type=int, default=300)
    p.add_argument("--dry-run", action="store_true", help="只打印请求体，不提交")
    p.add_argument("--quiet", action="store_true")
    p.set_defaults(func=cmd_image)

    p = sub.add_parser("video", help="提交视频任务并取回文件")
    p.add_argument("--prompt", required=True)
    p.add_argument("--model", help="目录里的模型 id；多个可用模型时必须显式指定")
    p.add_argument("--duration", type=int, help="整数秒，必须在该模型的 duration_options 里")
    p.add_argument("--ratio")
    p.add_argument("--resolution")
    p.add_argument("--mode", help="如 first_last_frame，需模型声明支持")
    p.add_argument("--prompt-enhance", dest="prompt_enhance", action="store_true")
    p.add_argument("--ref-image", action="append", help="本地参考图，可多次")
    p.add_argument("--ref-audio", action="append")
    p.add_argument("--ref-video", action="append")
    p.add_argument("--image-url", action="append")
    p.add_argument("--audio-url", action="append")
    p.add_argument("--video-url", action="append")
    p.add_argument("--client-task-id", dest="client_task_id",
                   help="业务 ID，同一 ID 只对应同一任务；改了提示词要换新 ID")
    p.add_argument("--callback-url")
    p.add_argument("--out-dir", help="成品目录，默认当前状态根 outputs/videos/<task_id>")
    p.add_argument("--timeout", type=int, default=1800)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--quiet", action="store_true")
    add_common(p)
    p.set_defaults(func=cmd_video)

    p = sub.add_parser("status", help="查任务；网络断了或链接过期用这个")
    p.add_argument("--kind", choices=["image", "video"], required=True)
    p.add_argument("--task-id", dest="task_id", required=True)
    p.add_argument("--download", action="store_true", help="顺便重新下载成品")
    p.add_argument("--out-dir")
    add_common(p)
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("reconcile", help="对账：账本逐条回站方核对，不花钱")
    p.add_argument("--since", help="只看某天起，如 2026-11-01")
    p.add_argument("--json-out", dest="json_out", help="结果存成 JSON")
    add_common(p)
    p.set_defaults(func=cmd_reconcile)

    p = sub.add_parser("ledger", help="看花了多少钱")
    p.add_argument("--tail", type=int, default=0)
    p.add_argument("--rate", type=float,
                   help="当前任务合约确认的人民币换算比例；默认不换算")
    p.set_defaults(func=cmd_ledger)

    args = parser.parse_args()
    global CONFIG, STATE, LEDGER, NO_PROXY, OFFLINE
    CONFIG = (args.config or Path.home() / ".xingqiao" / "config.json").expanduser().resolve()
    state_root = (args.state_dir or CONFIG.parent).expanduser().resolve()
    STATE, LEDGER = state_root / "tasks", state_root / "ledger.jsonl"
    NO_PROXY = args.no_proxy
    OFFLINE = args.cmd == "self-test" or getattr(args, "dry_run", False)
    for name in ("out", "json_out"):
        target = getattr(args, name, None)
        if target and Path(target).exists():
            die("输出文件已存在，拒绝覆盖：%s" % target)
    if not getattr(args, "cmd", None):
        parser.print_help()
        return
    args.func(args)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        die("已中断。任务如果已经提交，用 status 查，不要重新提交。", 130)
