#!/usr/bin/env python3
"""Direct Ark video and HMAC-signed asset requests; sanitized output by default."""

import argparse
import datetime as dt
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

VIDEO_BASE = "https://ark.cn-beijing.volces.com/api/v3"
ASSET_BASE = "https://ark.cn-beijing.volcengineapi.com/"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def load_env(path):
    if not path:
        return
    for line in Path(path).read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        key, sep, value = line.partition("=")
        if sep and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key.strip()):
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            os.environ.setdefault(key.strip(), value)


def required(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise ValueError("Missing environment variable: " + name)
    return value


def sign(url, body):
    ak = required("ARK_ASSET_ACCESS_KEY")
    sk = required("ARK_ASSET_SECRET_KEY")
    now = dt.datetime.now(dt.timezone.utc)
    stamp, day = now.strftime("%Y%m%dT%H%M%SZ"), now.strftime("%Y%m%d")
    parsed = urllib.parse.urlsplit(url)
    digest = hashlib.sha256(body).hexdigest()
    headers = {"content-type": "application/json", "host": parsed.netloc,
               "x-content-sha256": digest, "x-date": stamp}
    signed = ";".join(sorted(headers))
    canonical_headers = "".join(key + ":" + headers[key] + "\n" for key in sorted(headers))
    query = urllib.parse.urlencode(sorted(urllib.parse.parse_qsl(parsed.query)), quote_via=urllib.parse.quote)
    canonical = "\n".join(["POST", parsed.path or "/", query, canonical_headers, signed, digest])
    scope = day + "/cn-beijing/ark/request"
    to_sign = "\n".join(["HMAC-SHA256", stamp, scope, hashlib.sha256(canonical.encode()).hexdigest()])
    signing_key = sk.encode()
    for part in (day, "cn-beijing", "ark", "request"):
        signing_key = hmac.new(signing_key, part.encode(), hashlib.sha256).digest()
    signature = hmac.new(signing_key, to_sign.encode(), hashlib.sha256).hexdigest()
    headers["Authorization"] = "HMAC-SHA256 Credential=" + ak + "/" + scope + ", SignedHeaders=" + signed + ", Signature=" + signature
    return headers


def sanitize(value, field="", extra_secrets=()):
    sensitive = ("secret", "password", "authorization", "credential", "signature", "access_key", "apikey", "api_key")
    compact_field = field.lower().replace("_", "")
    if compact_field in {"token", "bytedtoken", "accesstoken", "refreshtoken"} or any(part in field.lower() for part in sensitive):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {key: sanitize(item, key, extra_secrets) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize(item, extra_secrets=extra_secrets) for item in value]
    if isinstance(value, str):
        # Media URLs may contain usable temporary credentials; even error text
        # can echo the request, so redact embedded URLs and known credentials.
        value = re.sub(r"https?://[^\s<>\"']+", "[URL_REDACTED]", value)
        for name in ("ARK_API_KEY", "ARK_ASSET_ACCESS_KEY", "ARK_ASSET_SECRET_KEY", "ARK_BYTED_TOKEN"):
            secret = os.environ.get(name, "")
            if secret:
                value = value.replace(secret, "[REDACTED]")
        for secret in extra_secrets:
            if secret:
                value = value.replace(secret, "[REDACTED]")
        return value
    return value


def request(method, url, payload=None, assets=False, private_output=None):
    body = None if payload is None else json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    headers = sign(url, body) if assets else {"Authorization": "Bearer " + required("ARK_API_KEY")}
    headers["Content-Type"] = "application/json"
    headers["Accept"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    opener = urllib.request.build_opener(NoRedirect())
    try:
        response = opener.open(req, timeout=30)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        status = response.code
        raw = response.read(2 * 1024 * 1024 + 1)
        if len(raw) > 2 * 1024 * 1024:
            raise ValueError("Response exceeds 2 MiB")
        try:
            data = json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            data = {"non_json_response": True}
        request_id = response.headers.get("X-Tt-Logid") or response.headers.get("X-Request-Id")
    if private_output:
        # Explicit opt-in only. Never overwrite an earlier session/result.
        with Path(private_output).open("x", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
    metadata = data.get("ResponseMetadata", {}) if isinstance(data, dict) else {}
    upstream_error = metadata.get("Error") or (data.get("error") if isinstance(data, dict) else None)
    extra_secrets = []
    if isinstance(payload, dict) and isinstance(payload.get("BytedToken"), str):
        extra_secrets.append(payload["BytedToken"])
    result = data.get("Result", {}) if isinstance(data, dict) else {}
    if isinstance(result, dict) and isinstance(result.get("BytedToken"), str):
        extra_secrets.append(result["BytedToken"])
    output = {"http_status": status, "request_id": metadata.get("RequestId") or request_id, "response": sanitize(data, extra_secrets=extra_secrets)}
    print(json.dumps(output, ensure_ascii=False))
    return 0 if 200 <= status < 300 and not upstream_error else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", help="Read a local ignored UTF-8 env file; existing process values win")
    parser.add_argument("--private-output", help="Opt-in raw JSON output to a NEW private local file; may contain H5 tokens or signed URLs")
    commands = parser.add_subparsers(dest="command", required=True)
    action = commands.add_parser("asset-action", help="HMAC-signed control-plane Action")
    action.add_argument("action")
    source = action.add_mutually_exclusive_group()
    source.add_argument("--body", default="{}")
    source.add_argument("--body-file", help="UTF-8 JSON object")
    action.add_argument("--allow-write", action="store_true")
    get = commands.add_parser("video-get")
    get.add_argument("task_id")
    commands.add_parser("video-list")
    create = commands.add_parser("video-create", help="Creates one billable task; no automatic retry")
    create.add_argument("--allow-charge", action="store_true")
    create.add_argument("--model", default="doubao-seedance-2-0-mini-260615")
    create.add_argument("--prompt", required=True)
    create.add_argument("--duration", type=int, default=5)
    create.add_argument("--resolution", choices=("480p", "720p"), default="480p")
    args = parser.parse_args()
    try:
        load_env(args.env_file)
        if args.private_output:
            destination = Path(args.private_output)
            if destination.exists():
                raise ValueError("Private output already exists; choose a NEW private local file")
            if not destination.parent.is_dir():
                raise ValueError("Private output parent directory does not exist")
        if args.command == "asset-action":
            readonly = {"ListAssetGroups", "GetAssetGroup", "ListAssets", "GetAsset", "ListAuthorizedFirstAssetByGroups", "GetVisualValidateResult"}
            if args.action not in readonly and not args.allow_write:
                raise ValueError("Mutating/unknown Action requires --allow-write and prior user authorization")
            if not re.fullmatch(r"[A-Za-z][A-Za-z0-9]{1,80}", args.action):
                raise ValueError("Invalid Action name")
            text = Path(args.body_file).read_text(encoding="utf-8-sig") if args.body_file else args.body
            payload = json.loads(text)
            if not isinstance(payload, dict):
                raise ValueError("Action body must be a JSON object")
            payload.setdefault("ProjectName", os.environ.get("ARK_ASSET_PROJECT_NAME", "default").strip() or "default")
            if args.action == "GetVisualValidateResult" and not payload.get("BytedToken"):
                payload["BytedToken"] = required("ARK_BYTED_TOKEN")
            if args.action == "CreateVisualValidateSession":
                callback = urllib.parse.urlsplit(payload.get("CallbackURL", ""))
                if callback.scheme != "https" or not callback.hostname or callback.username or callback.password:
                    raise ValueError("H5 creation requires an accessible public HTTPS CallbackURL")
            url = ASSET_BASE + "?" + urllib.parse.urlencode({"Action": args.action, "Version": "2024-01-01"})
            return request("POST", url, payload, assets=True, private_output=args.private_output)
        if args.command == "video-get":
            return request("GET", VIDEO_BASE + "/contents/generations/tasks/" + urllib.parse.quote(args.task_id, safe=""), private_output=args.private_output)
        if args.command == "video-list":
            return request("GET", VIDEO_BASE + "/contents/generations/tasks", private_output=args.private_output)
        if not args.allow_charge:
            raise ValueError("Video generation requires --allow-charge and prior user authorization")
        if not 4 <= args.duration <= 15:
            raise ValueError("This minimal generation helper accepts 4-15 seconds; other model modes require their own documented validation")
        payload = {"model": args.model, "content": [{"type": "text", "text": args.prompt}], "duration": args.duration,
                   "resolution": args.resolution, "ratio": "16:9", "generate_audio": False, "watermark": False}
        return request("POST", VIDEO_BASE + "/contents/generations/tasks", payload, private_output=args.private_output)
    except (ValueError, OSError, urllib.error.URLError) as error:
        # Do not print transport exception strings: proxy URLs may contain credentials.
        message = str(error) if isinstance(error, ValueError) else "Transport or local file operation failed; no automatic retry"
        print(json.dumps({"error": sanitize(message)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
