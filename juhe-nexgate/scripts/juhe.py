"""聚合服务辅助工具；仅使用 Python 标准库。"""
import argparse
import base64
import ctypes
from ctypes import wintypes
import getpass
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import time
from urllib import error, parse, request

DEFAULT_BASE = "https://juhe.top"
TTL = 900


class Failure(Exception):
    def __init__(self, kind, message):
        self.kind = kind
        super().__init__(message)


def config_dir():
    if os.name == "nt":
        root = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData/Local")
    else:
        root = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    directory = (root / "juhe-nexgate").resolve()
    skill = Path(__file__).resolve().parents[1]
    if directory == skill or skill in directory.parents or any((p / ".git").exists() for p in (directory, *directory.parents)):
        raise Failure("storage", "拒绝在技能目录或 Git 仓库中保存凭据与缓存。")
    return directory


def ensure_dir(path):
    missing = []
    current = path
    while not current.exists():
        missing.append(current)
        current = current.parent
    if not current.is_dir():
        raise Failure("storage", "配置父路径不是目录。")
    for directory in reversed(missing):
        directory.mkdir(mode=0o700)
    if path.is_symlink():
        raise Failure("storage", "配置目录不能为符号链接。")
    if os.name != "nt":
        if path.stat().st_uid != os.getuid():
            raise Failure("storage", "配置目录不属于当前用户。")
        path.chmod(0o700)


def write_private(path, data):
    ensure_dir(path.parent)
    fd, temporary = tempfile.mkstemp(prefix=".juhe-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            if os.name != "nt":
                os.fchmod(stream.fileno(), 0o600)
            json.dump(data, stream, ensure_ascii=False)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def dpapi(data, decrypt=False):
    if os.name != "nt":
        raise Failure("storage", "DPAPI 仅支持 Windows。")

    class Blob(ctypes.Structure):
        _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_ubyte))]

    buffer = ctypes.create_string_buffer(data)
    source = Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    target = Blob()
    crypt = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    function = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    function.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p,
                         ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    function.restype = wintypes.BOOL
    # UI_FORBIDDEN；不设置 LOCAL_MACHINE，绑定当前 Windows 用户。
    if not function(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(target)):
        raise Failure("storage", "DPAPI 操作失败；请使用保存凭据的 Windows 用户。")
    try:
        return ctypes.string_at(target.data, target.size)
    finally:
        kernel.LocalFree(ctypes.cast(target.data, ctypes.c_void_p))


def save_key(key, directory=None):
    if not key or any(c.isspace() for c in key):
        raise Failure("credential", "Key 不能为空或包含空白。")
    directory = directory or config_dir()
    if os.name == "nt":
        record = {"format": "dpapi-user-v1", "payload": base64.b64encode(dpapi(key.encode())).decode()}
    else:
        record = {"format": "posix-0600-v1", "payload": key}
    write_private(directory / "credential.json", record)
    clear_cache(directory)


def clear_saved(directory=None):
    directory = directory or config_dir()
    path = directory / "credential.json"
    existed = path.exists()
    path.unlink(missing_ok=True)
    clear_cache(directory)
    return {"cleared": existed, "configured": False, "source": "missing",
            "saved_exists": False, "validated": False, "ask_user_for_key": True}


def read_stream_key(stream):
    """从管道读取用户提交的 Key；只在内存中处理，不回显、不记录。"""
    try:
        if stream.isatty():
            raise Failure("interaction", "--stdin 只接受管道输入；交互终端请运行 auth set 隐藏输入。")
    except (AttributeError, OSError):
        raise Failure("interaction", "无法确认输入来源；请改用 auth set 隐藏输入。") from None
    try:
        value = stream.read()
    except (OSError, UnicodeError):
        raise Failure("interaction", "读取输入失败。") from None
    value = value.strip()
    if not value:
        raise Failure("credential", "输入为空，未保存。")
    return value


def read_saved(directory=None):
    path = (directory or config_dir()) / "credential.json"
    if not path.exists():
        return None
    try:
        if path.is_symlink():
            raise ValueError()
        if os.name != "nt":
            info = path.stat()
            if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600:
                raise ValueError()
        record = json.loads(path.read_text(encoding="utf-8"))
        if os.name == "nt" and record["format"] == "dpapi-user-v1":
            key = dpapi(base64.b64decode(record["payload"], validate=True), True).decode()
        elif os.name != "nt" and record["format"] == "posix-0600-v1":
            key = record["payload"]
        else:
            raise ValueError()
        if not isinstance(key, str) or not key or any(c.isspace() for c in key):
            raise ValueError()
        return key
    except Failure:
        raise
    except (OSError, ValueError, KeyError, TypeError):
        raise Failure("storage", "已保存凭据不可读或权限不安全；不要据此判断为缺失。") from None


def credential(directory=None):
    key = os.environ.get("JUHE_API_KEY", "").strip()
    if key:
        if any(c.isspace() for c in key):
            raise Failure("credential", "环境变量凭据包含空白。")
        return key, "environment"
    key = read_saved(directory)
    return key, "saved" if key else "missing"


def status(directory=None):
    key, source = credential(directory)
    return {"configured": bool(key), "source": source,
            "saved_exists": ((directory or config_dir()) / "credential.json").exists(),
            "validated": False,
            # 供技能判断是否可以主动向用户索取 Key：已配置时必须停止询问。
            "ask_user_for_key": not key}


def base_url(value):
    parts = parse.urlsplit(value)
    if (parts.scheme != "https" or not parts.hostname or parts.username or parts.password
            or parts.query or parts.fragment or parts.path not in ("", "/")):
        raise Failure("config", "Base URL 必须为无凭据、路径、查询串的 HTTPS 服务根地址。")
    return value.rstrip("/")


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch_models(base, key):
    req = request.Request(base + "/v1/models", headers={"Authorization": "Bearer " + key})
    try:
        with request.build_opener(NoRedirect()).open(req, timeout=30) as response:
            payload = json.load(response)
    except error.HTTPError as exc:
        if exc.code == 401:
            raise Failure("unauthorized", "HTTP 401：当前凭据被拒绝；检查来源，环境变量优先。") from None
        raise Failure("http", "HTTP %s：服务拒绝请求；不输出响应正文。" % exc.code) from None
    except (error.URLError, TimeoutError, OSError):
        raise Failure("network", "网络、TLS 或超时错误；不代表 Key 失效。") from None
    except ValueError:
        raise Failure("response", "服务返回的 JSON 无效。") from None
    if (not isinstance(payload, dict) or not isinstance(payload.get("data"), list)
            or any(not isinstance(row, dict) or not isinstance(row.get("id"), str)
                   or not row["id"] for row in payload["data"])):
        raise Failure("response", "模型列表缺少有效的 data[].id。")
    return sorted(set(row["id"] for row in payload["data"]))


def clear_cache(directory=None):
    path = (directory or config_dir()) / "models-cache.json"
    path.unlink(missing_ok=True)


def get_models(base, key, cached=False, directory=None):
    directory = directory or config_dir()
    path = directory / "models-cache.json"
    # 哈希只用于隔离缓存，不用于鉴权，不保存 Key 或其片段。
    scope = hashlib.sha256((base + "\0" + key).encode()).hexdigest()
    if cached:
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            age = time.time() - record["time"]
            if (record["scope"] == scope and 0 <= age < TTL
                    and isinstance(record["ids"], list)
                    and all(isinstance(x, str) and x for x in record["ids"])):
                return record["ids"], "cache"
        except (OSError, ValueError, KeyError, TypeError):
            pass
    try:
        ids = fetch_models(base, key)
    except Failure as exc:
        if exc.kind == "unauthorized":
            clear_cache(directory)
        raise
    write_private(path, {"scope": scope, "time": time.time(), "ids": ids})
    return ids, "live"


# 仅登记随技能提供的参考文件中明确列出的完整 ID，不按名称猜新型号能力。
KNOWN = {}


def register(ids, family, tasks, endpoint):
    for model in ids.split():
        KNOWN[model] = {"family": family, "tasks": tasks, "endpoint": endpoint,
                        "capability_source": "bundled-references"}


register("gpt-5.6-luna gpt-5.6-sol gpt-5.6-terra gpt-6-astra gpt-6-luna gpt-6-sol gpt-6.1-sol", "gpt", ["chat"], "/v1/chat/completions")
register("claude-fable-5-1 claude-opus-4-8 claude-opus-5-5", "claude", ["chat"], "/v1/chat/completions")
register("deepseek-v4-flash deepseek-v4-pro deepseek-v4.1-flash", "deepseek", ["chat"], "/v1/chat/completions")
register("gemini-3.5-flash gemini-3.6-flash", "gemini", ["chat"], "/v1/chat/completions")
register("glm-5.2 glm-5.3", "glm", ["chat"], "/v1/chat/completions")
register("kimi-k3", "kimi", ["chat"], "/v1/chat/completions")
register("qwen3.5-flash qwen3.5-plus qwen3.6-flash qwen3.6-plus qwen3.8-27b qwen3.8-flash qwen3.8-max", "qwen", ["chat"], "/v1/chat/completions")
register("gpt-image-2 gpt-image-2.5-flare gpt-image-2.5-sunburst", "image-2", ["image", "image-edit"], "/v1/images/generations")
register("qwen-image-3.0", "qwen", ["image"], "/v1/images/generations")
register("wan2.7-image-pro", "wan", ["image"], "/v1/images/generations")
register("wan2.6-image", "wan", ["image-edit"], "/v1/images/edits")
register("doubao-seedance-2-0-260128 doubao-seedance-2-0-fast-260128", "seedance", ["video", "image-to-video", "reference-video"], "/api/v3/contents/generations/tasks")
register("doubao-seedance-2-0-mini-260615 doubao-seedance-2-5-260628", "seedance", ["video"], "/v1/videos")
register("happyhorse-1.1-t2v", "happyhorse", ["video"], "/v1/videos")
register("happyhorse-1.1-i2v", "happyhorse", ["image-to-video"], "/v1/videos")
register("happyhorse-1.1-r2v", "happyhorse", ["reference-image-to-video"], "/v1/videos")
register("happyhorse-1.0-video-edit", "happyhorse", ["video-edit"], "/v1/videos")
register("wan3.0-video-prime", "wan", ["video"], "/v1/videos")

ALIASES = {"千问": "qwen", "通义千问": "qwen", "通义": "qwen", "豆包": "seedance",
           "即梦": "seedance", "深度求索": "deepseek", "智谱": "glm", "月之暗面": "kimi",
           "可米": "kimi", "万相": "wan", "通义万相": "wan", "快乐马": "happyhorse",
           "image2": "image-2", "image 2": "image-2", "gpt image": "image-2"}
TASKS = {"聊天": "chat", "文本": "chat", "绘图": "image", "生图": "image", "文生图": "image",
         "图片编辑": "image-edit", "改图": "image-edit", "视频": "video", "文生视频": "video",
         "图生视频": "image-to-video", "参考图生视频": "reference-image-to-video",
         "参考视频": "reference-video", "视频编辑": "video-edit"}


def describe(model, task=None):
    info = KNOWN.get(model)
    if not info:
        return {"id": model, "tasks": [], "capability_source": "unknown", "note": "能力未知，需查证服务文档；不自动调用。"}
    result = {"id": model, **info}
    if task == "image-edit" and model.startswith("gpt-image-"):
        result["endpoint"] = "/v1/images/edits"
    return result


def resolve(ids, alias, task):
    task = TASKS.get(task.casefold(), task.casefold())
    if task not in set(TASKS.values()):
        raise Failure("task", "未知任务；请使用明确的 chat/image/image-edit/video 等任务名。")
    query = alias.strip().casefold()
    family = ALIASES.get(query, query)
    exact = [m for m in ids if m.casefold() == query]
    matched = exact or [m for m in ids if KNOWN.get(m, {}).get("family") == family]
    candidates = [describe(m, task) for m in matched if task in KNOWN.get(m, {}).get("tasks", [])]
    unknown = [describe(m) for m in matched if m not in KNOWN]
    return {"task": task, "candidates": candidates, "unknown": unknown,
            "selected": candidates[0]["id"] if len(candidates) == 1 else None,
            "note": "仅一个已知候选时自动选择；多个候选须明确完整 ID，不按名称猜优劣或能力。"}


def main(argv=None):
    parser = argparse.ArgumentParser(description="安全凭据、实时型号与任务别名解析（不执行生成）")
    sub = parser.add_subparsers(dest="command", required=True)
    auth = sub.add_parser("auth")
    auth.add_argument("action", choices=["status", "set", "clear"])
    auth.add_argument("--stdin", action="store_true",
                      help="从管道读取用户提交的 Key 并加密保存；不接受命令行明文 Key")
    sub.add_parser("cache-clear")
    for name in ("models", "resolve"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--base-url", default=os.environ.get("JUHE_BASE_URL", DEFAULT_BASE))
        cmd.add_argument("--cached", action="store_true", help="允许使用15分钟内同服务同凭据的缓存；默认实时")
        if name == "resolve":
            cmd.add_argument("alias")
            cmd.add_argument("--task", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "auth":
            if args.action == "clear":
                result = clear_saved()
            elif args.action == "set":
                if args.stdin:
                    save_key(read_stream_key(sys.stdin))
                else:
                    if not sys.stdin.isatty():
                        raise Failure("interaction", "交互保存需要终端；非交互环境请用 --stdin 从管道提交，或用环境变量。")
                    if os.name != "nt":
                        print("注意：非 Windows 仅以目录0700/文件0600保存明文，不提供磁盘加密。", file=sys.stderr)
                    import warnings
                    with warnings.catch_warnings():
                        warnings.simplefilter("error", getpass.GetPassWarning)
                        try:
                            value = getpass.getpass("输入 API Key（隐藏输入）：")
                        except (getpass.GetPassWarning, EOFError):
                            raise Failure("interaction", "无法保证隐藏输入，已取消保存。") from None
                    save_key(value)
                result = status()
            else:
                result = status()
        elif args.command == "cache-clear":
            clear_cache()
            result = {"cleared": True}
        else:
            key, source = credential()
            if not key:
                raise Failure("missing_credential", "环境变量与安全存储均未配置；向用户索取 Key 后用 auth set --stdin 保存，之后不再重复询问。")
            ids, origin = get_models(base_url(args.base_url), key, args.cached)
            result = ({"models": [describe(m) for m in ids]} if args.command == "models"
                      else resolve(ids, args.alias, args.task))
            result.update({"source": origin, "credential_source": source,
                           "warning": "列表可见不等于健康、额度充足或接口可用；能力来自随附参考，非服务实时能力声明。"})
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Failure as exc:
        print(json.dumps({"error": exc.kind, "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    except (OSError, ValueError):
        print('{"error":"storage_or_config","message":"本地配置或存储操作失败；未输出原始异常。"}', file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
