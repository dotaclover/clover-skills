#!/usr/bin/env python3
"""List Qianfan models or send one explicitly authorized chat request."""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request


def required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"Missing environment variable: {name}")
    return value


def request(endpoint: str, api_key: str, method: str, body: bytes | None = None) -> int:
    headers = {"Authorization": f"Bearer {api_key}"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(endpoint, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            print(f"HTTP {response.status}")
            print(response.read().decode("utf-8", errors="replace"))
            return 0
    except urllib.error.HTTPError as exc:
        print(f"HTTP {exc.code}", file=sys.stderr)
        print(exc.read().decode("utf-8", errors="replace"), file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(f"Network error: {exc.reason}", file=sys.stderr)
        return 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("models", help="List models; read-only")
    chat = commands.add_parser("chat", help="Send one minimal Chat Completions request")
    chat.add_argument("--model", required=True)
    chat.add_argument("--prompt", default="你好")
    chat.add_argument("--send", action="store_true", help="Required: send a potentially billed request")
    args = parser.parse_args()

    base_url = required_env("BAIDU_QF_URL").rstrip("/")
    api_key = required_env("BAIDU_QF_KEY")
    if args.command == "models":
        return request(f"{base_url}/v1/models", api_key, "GET")
    if not args.send:
        parser.error("Refusing to send a request without --send")
    body = json.dumps({
        "model": args.model,
        "messages": [{"role": "user", "content": args.prompt}],
        "max_tokens": 64,
        "stream": False,
    }).encode("utf-8")
    return request(f"{base_url}/v2/chat/completions", api_key, "POST", body)


if __name__ == "__main__":
    raise SystemExit(main())
