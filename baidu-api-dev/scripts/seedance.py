#!/usr/bin/env python3
"""Baidu AI gateway Seedance client. Standard library; sanitized output only."""

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid


READ_ACTIONS = {
    "GetAssetGroup", "ListAssetGroups", "GetAsset", "ListAssets",
    "GetVisualValidateResult", "ListAuthorizedFirstAssetByGroups",
}
WRITE_ACTIONS = {
    "CreateAssetGroup", "UpdateAssetGroup", "DeleteAssetGroup",
    "CreateAsset", "UpdateAsset", "DeleteAsset", "CreateVisualValidateSession",
}
SENSITIVE_FIELDS = {"authorization", "bytedtoken", "h5link", "apikey", "api_key", "secretkey", "accesskey", "token", "cookie"}


def load_env(path):
    if not path:
        return
    for raw in Path(path).read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        name, separator, value = line.partition("=")
        name = name.strip()
        if separator and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            os.environ.setdefault(name, value)


def sanitize(value, secrets):
    if isinstance(value, dict):
        return {name: ("[REDACTED]" if name.lower() in SENSITIVE_FIELDS else sanitize(item, secrets)) for name, item in value.items()}
    if isinstance(value, list):
        return [sanitize(item, secrets) for item in value]
    if isinstance(value, str):
        for secret in secrets:
            value = value.replace(secret, "[REDACTED]")
        return re.sub(r"https?://[^\s\"'<>]+", "[URL REDACTED]", value)
    return value


class Client:
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    def __init__(self, base, api_key, timeout, private_output=None):
        parsed = urllib.parse.urlsplit(base)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path.rstrip("/"):
            raise ValueError("BAIDU_AI_URL must be an HTTPS origin, without credentials, query, or API path")
        self.base = base.rstrip("/")
        self.key = api_key
        self.secrets = {api_key}
        self.timeout = timeout
        self.private_output = Path(private_output) if private_output else None
        self.opener = urllib.request.build_opener(self.NoRedirect())

    def request(self, label, method, path, body=None):
        if isinstance(body, dict) and isinstance(body.get("BytedToken"), str):
            self.secrets.add(body["BytedToken"])
        encoded = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(self.base + path, data=encoded, method=method, headers={"Authorization": "Bearer " + self.key, "Content-Type": "application/json", "Accept": "application/json"})
        started = time.monotonic()
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                status, headers, raw = response.status, response.headers, response.read(2_000_001)
        except urllib.error.HTTPError as error:
            status, headers, raw = error.code, error.headers, error.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ValueError("response exceeds 2 MB safety limit")
        try:
            result = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            result = {"non_json_response": True, "bytes": len(raw)}
        if isinstance(result, dict) and isinstance(result.get("Result"), dict):
            token = result["Result"].get("BytedToken")
            if isinstance(token, str) and token:
                self.secrets.add(token)
        if self.private_output:
            # H5Link and BytedToken are usable short-lived credentials. Raw
            # output is explicit, local, exclusive-create, and only allowed
            # for one operation so a smoke run cannot persist account lists.
            with self.private_output.open("x", encoding="utf-8") as handle:
                json.dump(result, handle, ensure_ascii=False, indent=2)
        public_result = sanitize(result, self.secrets)
        if isinstance(public_result, dict) and isinstance(public_result.get("Result"), dict):
            items = public_result["Result"].get("Items")
            if isinstance(items, (list, dict)):
                records = items if isinstance(items, list) else list(items.values())
                public_result["Result"]["Items"] = {
                    "returned_count": len(records),
                    "statuses": sorted({item["Status"] for item in records if isinstance(item, dict) and isinstance(item.get("Status"), str)}),
                    "group_types": sorted({item["GroupType"] for item in records if isinstance(item, dict) and isinstance(item.get("GroupType"), str)}),
                }
        report = {"operation": label, "http_status": status, "elapsed_seconds": round(time.monotonic() - started, 3), "response": public_result}
        for name in ("x-request-id", "x-tt-logid", "x-bce-request-id"):
            if headers.get(name):
                report[name] = headers[name]
        print(json.dumps(report, ensure_ascii=False), flush=True)
        return status, result

    def action(self, name, body):
        return self.request(name, "POST", "/?" + urllib.parse.urlencode({"Action": name, "Version": "2024-01-01"}), body)


def smoke(client, args):
    project = args.project
    base = {"ProjectName": project}
    for group_type in ("AIGC", "LivenessFace"):
        for action in ("ListAssetGroups", "ListAssets"):
            client.action(action, {**base, "Filter": {"GroupType": group_type}, "PageNumber": 1, "PageSize": 10})
    marker = "skill-seedance-bd-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6]
    group_id = None
    try:
        status, response = client.action("CreateAssetGroup", {**base, "GroupType": "AIGC", "Name": marker, "Description": "Temporary skill API verification; delete this test group only"})
        if status == 200:
            group_id = response.get("Result", {}).get("Id")
        if group_id:
            client.action("GetAssetGroup", {**base, "Id": group_id})
            client.action("UpdateAssetGroup", {**base, "Id": group_id, "Name": marker + "-updated"})
            client.action("GetAssetGroup", {**base, "Id": group_id})
            client.action("ListAssets", {**base, "Filter": {"GroupType": "AIGC", "GroupIds": [group_id]}, "PageNumber": 1, "PageSize": 10})
    finally:
        if group_id:
            status, _ = client.action("DeleteAssetGroup", {**base, "Id": group_id})
            print(json.dumps({"cleanup_group_id": group_id, "cleanup_succeeded": status == 200}, ensure_ascii=False), flush=True)
    status, response = client.action("CreateVisualValidateSession", {**base, "CallbackURL": args.callback_url})
    result = response.get("Result", {}) if isinstance(response, dict) else {}
    token = result.get("BytedToken")
    print(json.dumps({"h5_created": status == 200, "has_h5_link": bool(result.get("H5Link")), "has_byted_token": bool(token), "human_consent_performed": False}), flush=True)
    if status == 200 and token:
        client.action("GetVisualValidateResult", {**base, "BytedToken": token})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", help="Explicit local .env path; process environment takes precedence")
    parser.add_argument("--timeout", type=float, default=90)
    parser.add_argument("--private-output", help="Write one raw response to a NEW private local file; may contain H5 token or signed URLs")
    commands = parser.add_subparsers(dest="command", required=True)
    action = commands.add_parser("action")
    action.add_argument("name", choices=sorted(READ_ACTIONS | WRITE_ACTIONS))
    action.add_argument("--body", default="{}", help="JSON object; do not pass secrets on the command line")
    action.add_argument("--allow-write", action="store_true")
    create = commands.add_parser("video-create")
    create.add_argument("--body-file", required=True, help="UTF-8 JSON body, Ark format")
    create.add_argument("--allow-charge", action="store_true")
    get = commands.add_parser("video-get")
    get.add_argument("task_id")
    h5 = commands.add_parser("h5-create")
    h5.add_argument("--project", default="default")
    h5.add_argument("--callback-url", required=True)
    h5.add_argument("--allow-write", action="store_true")
    result = commands.add_parser("h5-result")
    result.add_argument("--project", default="default")
    check = commands.add_parser("smoke")
    check.add_argument("--project", default="default")
    check.add_argument("--callback-url", required=True)
    check.add_argument("--allow-write", action="store_true")
    args = parser.parse_args()
    load_env(args.env_file)
    base = os.environ.get("BAIDU_AI_URL", "")
    api_key = os.environ.get("BAIDU_AI_KEY", "")
    if not base or not api_key:
        parser.error("BAIDU_AI_URL and BAIDU_AI_KEY must be explicitly configured")
    if args.timeout <= 0 or args.timeout > 300:
        parser.error("--timeout must be in (0, 300]")
    needs_write = args.command in {"smoke", "h5-create"} or (args.command == "action" and args.name in WRITE_ACTIONS)
    if needs_write and not args.allow_write:
        parser.error("this operation requires user authorization and --allow-write")
    if args.command == "video-create" and not args.allow_charge:
        parser.error("video creation requires paid-operation authorization and --allow-charge")
    if args.private_output and args.command == "smoke":
        parser.error("--private-output cannot be combined with smoke; use one explicit action")
    if args.private_output:
        destination = Path(args.private_output)
        if destination.exists() or not destination.parent.is_dir():
            parser.error("--private-output must name a NEW file under an existing private directory")
    client = Client(base, api_key, args.timeout, args.private_output)
    if args.command == "action":
        body = json.loads(args.body)
        if not isinstance(body, dict):
            parser.error("--body must be a JSON object")
        status, _ = client.action(args.name, body)
    elif args.command == "video-create":
        body = json.loads(Path(args.body_file).read_text(encoding="utf-8-sig"))
        if not isinstance(body, dict):
            parser.error("--body-file must contain a JSON object")
        status, _ = client.request("video-create", "POST", "/api/v3/contents/generations/tasks", body)
    elif args.command == "video-get":
        status, _ = client.request("video-get", "GET", "/api/v3/contents/generations/tasks/" + urllib.parse.quote(args.task_id, safe=""))
    elif args.command == "h5-create":
        status, _ = client.action("CreateVisualValidateSession", {"ProjectName": args.project, "CallbackURL": args.callback_url})
    elif args.command == "h5-result":
        token = os.environ.get("BAIDU_SEEDANCE_BYTED_TOKEN", "")
        if not token:
            parser.error("set BAIDU_SEEDANCE_BYTED_TOKEN privately; do not put the token in command arguments")
        status, _ = client.action("GetVisualValidateResult", {"ProjectName": args.project, "BytedToken": token})
    else:
        smoke(client, args)
        return 0
    return 0 if 200 <= status < 300 else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, urllib.error.URLError) as error:
        # Do not leak request URLs, query strings or credential-bearing error bodies.
        print(json.dumps({"client_error": type(error).__name__, "message": "Request/configuration failed; inspect private configuration and the preceding sanitized responses."}), file=sys.stderr)
        sys.exit(2)
