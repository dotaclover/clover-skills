#!/usr/bin/env python3
"""Send one explicit, minimal Baidu VOD Chat Completions request."""

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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=("old", "new"), required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--prompt", default="你好")
    parser.add_argument("--send", action="store_true", help="Required: send a potentially billed request")
    args = parser.parse_args()

    if not args.send:
        parser.error("Refusing to send a request without --send")

    prefix = "BAIDU_VOD" if args.provider == "old" else "BAIDU_NEWVOD"
    base_url = required_env(f"{prefix}_URL").rstrip("/")
    api_key = required_env(f"{prefix}_KEY")
    endpoint = f"{base_url}/v1/chat/completions"
    payload = json.dumps({
        "model": args.model,
        "messages": [{"role": "user", "content": args.prompt}],
        "max_tokens": 64,
        "stream": False,
    }).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=payload,
        method="POST",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = response.read().decode("utf-8", errors="replace")
            print(f"HTTP {response.status}")
            print(body)
            return 0
    except urllib.error.HTTPError as exc:
        print(f"HTTP {exc.code}", file=sys.stderr)
        print(exc.read().decode("utf-8", errors="replace"), file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(f"Network error: {exc.reason}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
\n