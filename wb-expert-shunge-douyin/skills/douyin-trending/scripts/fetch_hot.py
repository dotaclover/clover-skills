#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抖音热榜取数（零依赖）。

只用标准库，不发任何写请求。默认打印榜单表格，可选落盘。

用法：
    python fetch_hot.py                     # 打印前 50 条
    python fetch_hot.py --top 20            # 只打印前 20 条
    python fetch_hot.py --json hot.json     # 另存原始响应
    python fetch_hot.py --out hot.md        # 另存 markdown 表格
    python fetch_hot.py --direct            # 绕过系统代理（代理异常时用）

接口非官方公开文档，字段可能变化；失败时如实报错，不猜数据。
"""
import argparse
import json
import sys
import urllib.request

URL = "https://www.iesdouyin.com/web/api/v2/hotsearch/billboard/word/"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")


def fetch(direct=False, timeout=20):
    req = urllib.request.Request(URL, headers={"User-Agent": UA})
    if direct:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    else:
        opener = urllib.request.build_opener()
    with opener.open(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    data = json.loads(raw)
    if data.get("status_code") != 0:
        raise RuntimeError(f"接口返回非成功状态：status_code={data.get('status_code')}")
    items = data.get("word_list") or []
    if not items:
        raise RuntimeError("接口返回空榜单，可能接口已变更")
    return data, items, raw


def fmt(n):
    return f"{int(n):,}" if isinstance(n, (int, float)) else str(n)


def to_markdown(items, active_time, top):
    lines = [f"取数时间：{active_time}", "",
             "| 排名 | 标题原文 | 热度 | 标记 |", "|---|---|---|---|"]
    for i, w in enumerate(items[:top], 1):
        lines.append(f"| {i} | {w.get('word','')} | {fmt(w.get('hot_value',0))} | {w.get('label','')} |")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=50)
    ap.add_argument("--json", dest="json_path")
    ap.add_argument("--out", dest="out_path")
    ap.add_argument("--direct", action="store_true", help="绕过系统代理")
    args = ap.parse_args()

    try:
        data, items, raw = fetch(direct=args.direct)
    except Exception as e:
        print(f"取数失败：{type(e).__name__}: {e}", file=sys.stderr)
        print("可尝试：加 --direct 绕过代理；仍失败则改用浏览器打开热榜页人工读取。", file=sys.stderr)
        return 1

    active = data.get("active_time", "未知")
    md = to_markdown(items, active, args.top)
    print(md)

    if args.json_path:
        with open(args.json_path, "w", encoding="utf-8") as f:
            f.write(raw)
        print(f"\n原始响应已存：{args.json_path}", file=sys.stderr)
    if args.out_path:
        with open(args.out_path, "w", encoding="utf-8") as f:
            f.write(md + "\n")
        print(f"表格已存：{args.out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
