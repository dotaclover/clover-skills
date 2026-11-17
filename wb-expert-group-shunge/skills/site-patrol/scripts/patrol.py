#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""官网巡检与收录推送（仅用于 www.cloverphp.top，私有站点专用）。

站点事实、验证文件内容和推送凭证硬编码在本文件里，不再依赖任何私有目录。
只读巡检默认关闭代理（本机 http_proxy 会把数据推到别处，百度接口此前因此卡住）。

用法：
    python expert/skills/site-patrol/scripts/patrol.py check
    python expert/skills/site-patrol/scripts/patrol.py check --json
    python expert/skills/site-patrol/scripts/patrol.py push-baidu
    python expert/skills/site-patrol/scripts/patrol.py push-indexnow
    python expert/skills/site-patrol/scripts/patrol.py push

退出码：检查项失败或推送未成功为 1，否则为 0。
"""
from __future__ import annotations

import argparse
import json
import re
import socket
import sys
import urllib.error
import urllib.request
from pathlib import Path

HOST = "www.cloverphp.top"
BASE = "https://" + HOST + "/"

# 与 sitemap.xml 一致的 7 条规范 URL；推送只用这一组。
URLS = [
    BASE,
    BASE + "services/",
    BASE + "works/",
    BASE + "about/",
    BASE + "contact/",
    BASE + "privacy/",
    BASE + "terms/",
]

# 必须常驻站点根目录的验证文件：文件名 -> 精确内容（换行是 \n，BingSiteAuth.xml 用 Tab 缩进、无末尾换行）。
VERIFY_FILES = {
    "baidu_verify_codeva-AGYbWYiiUk.html": "6444b007b6d9b8ba98a651a7ec4462e9",
    "google30c2d54585ab44c5.html": "google-site-verification: google30c2d54585ab44c5.html",
    "BingSiteAuth.xml": (
        '<?xml version="1.0"?>\n'
        "<users>\n"
        "\t<user>2C255945B48296FED197A262E7E12973</user>\n"
        "</users>"
    ),
    "adfe6fc0c85bac1e7ea4274f0f0ee94e.txt": "adfe6fc0c85bac1e7ea4274f0f0ee94e",
}

BAIDU_TOKEN = "lHILT18x8xLDnolq"  # x 小写、l 小写 L；截图误读的 lHILT18x8XLDnloq 是错的
BAIDU_API = "http://data.zz.baidu.com/urls?site=" + BASE.rstrip("/") + "&token=" + BAIDU_TOKEN
INDEXNOW_KEY = "adfe6fc0c85bac1e7ea4274f0f0ee94e"
INDEXNOW_API = "https://api.indexnow.org/indexnow"
KEY_LOCATION = BASE + INDEXNOW_KEY + ".txt"

TIMEOUT = 20
NO_PROXY = urllib.request.ProxyHandler({})


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch(url: str, *, data=None, method="GET", headers=None, follow=True, timeout=TIMEOUT):
    """返回 (状态码, 响应头字典, 文本正文)；网络异常时状态码为 None。"""
    handlers = [NO_PROXY]
    if not follow:
        handlers.append(NoRedirect())
    opener = urllib.request.build_opener(*handlers)
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with opener.open(req, timeout=timeout) as resp:
            return resp.status, dict(resp.headers), resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read().decode("utf-8", "replace")
    except Exception as exc:  # noqa: BLE001 - 巡检脚本要把网络异常变成一行结论
        return None, {}, str(exc)


def mask(token: str) -> str:
    return token[:4] + "…" + token[-4:]


def find_repo(explicit: str | None) -> Path | None:
    if explicit:
        return Path(explicit).expanduser().resolve()
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "sites" / "cloverphp.top" / "index.html").is_file():
            return parent
    return None


def local_snapshot(repo: Path | None, rows: list) -> None:
    if repo is None:
        rows.append(("本地快照：找到仓库根目录", None, "未找到 sites/cloverphp.top，跳过本地项（安装副本里属正常）"))
        return
    root = repo / "sites" / "cloverphp.top"
    rows.append(("本地快照：index.html 存在", (root / "index.html").is_file(), str(root)))
    for name, expected in VERIFY_FILES.items():
        path = root / name
        if not path.is_file():
            rows.append((f"本地快照：{name} 在", False, "缺失"))
            continue
        actual = path.read_text(encoding="utf-8", errors="replace")
        rows.append((f"本地快照：{name} 内容正确", actual == expected,
                     "逐字节一致" if actual == expected else "内容与硬编码值不一致"))


def online(rows: list) -> None:
    try:
        infos = socket.gethostbyname_ex(HOST)
        rows.append(("DNS：解析到 IP", bool(infos[2]), ", ".join(infos[2])))
    except Exception as exc:  # noqa: BLE001
        rows.append(("DNS：解析到 IP", False, str(exc)))

    status, headers, _ = fetch("http://" + HOST + "/", follow=False)
    location = headers.get("Location", "")
    ok = status in (301, 302, 308) and BASE.rstrip("/") in location
    rows.append(("HTTP 跳到 https www（301）", ok, f"{status} -> {location}"))

    for url in URLS:
        status, _, body = fetch(url)
        rows.append((f"线上：{url} 返回 200", status == 200, f"状态码 {status}"))
        if status != 200:
            continue
        m = re.search(r'rel="canonical"\s+href="([^"]+)"', body)
        rows.append((f"线上：{url.rsplit('/', 2)[-2] or '首页'} canonical 指向本站",
                     bool(m and HOST in m.group(1)), m.group(1) if m else "缺 canonical"))
        rows.append((f"线上：{url.rsplit('/', 2)[-2] or '首页'} 无 noindex",
                     'content="noindex' not in body, ""))

    status, _, robots = fetch(BASE + "robots.txt")
    rows.append(("线上：robots.txt 放行", status == 200 and "Allow: /" in robots,
                 f"状态码 {status}"))
    status, _, sitemap = fetch(BASE + "sitemap.xml")
    locs = re.findall(r"<loc>([^<]+)</loc>", sitemap)
    foreign = [u for u in locs if HOST not in u]
    rows.append(("线上：sitemap 7 条且都指向本站",
                 status == 200 and len(locs) >= len(URLS) and not foreign,
                 f"状态码 {status}，{len(locs)} 条，异域名 {foreign[:2]}"))

    for name, expected in VERIFY_FILES.items():
        status, _, body = fetch(BASE + name)
        ok = status == 200 and body == expected
        rows.append((f"线上：{name} 可达且内容正确", ok,
                     f"状态码 {status}" + ("" if ok else "，内容不一致")))


def push_baidu(rows: list) -> None:
    body = ("\n".join(URLS) + "\n").encode("utf-8")
    safe_url = BAIDU_API.replace(BAIDU_TOKEN, mask(BAIDU_TOKEN))
    status, _, text = fetch(BAIDU_API, data=body, method="POST",
                            headers={"Content-Type": "text/plain"})
    ok = status == 200 and '"success"' in text
    rows.append((f"百度普通收录推送（token {mask(BAIDU_TOKEN)}）", ok,
                 f"{safe_url} -> {status} {text.strip()}"))


def push_indexnow(rows: list) -> None:
    payload = {
        "host": HOST,
        "key": INDEXNOW_KEY,
        "keyLocation": KEY_LOCATION,
        "urlList": URLS,
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    status, _, text = fetch(INDEXNOW_API, data=data, method="POST",
                            headers={"Content-Type": "application/json; charset=utf-8"})
    ok = status in (200, 202)
    rows.append((f"必应 IndexNow 推送（key {mask(INDEXNOW_KEY)}）", ok,
                 f"HTTP {status} {text.strip()}"))


def emit(rows: list, as_json: bool) -> int:
    failed = [r for r in rows if r[1] is False]
    skipped = [r for r in rows if r[1] is None]
    if as_json:
        print(json.dumps([
            {"item": name, "ok": ok, "detail": detail} for name, ok, detail in rows
        ], ensure_ascii=False, indent=2))
    else:
        for name, ok, detail in rows:
            if ok is False:
                print(f"失败  {name}  {detail}")
        for name, ok, detail in rows:
            if ok is None:
                print(f"跳过  {name}  {detail}")
        print(f"{len(rows) - len(failed) - len(skipped)}/{len(rows) - len(skipped)} 项通过")
    return 1 if failed else 0


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", help="输出 JSON 证据")
    common.add_argument("--repo", help="仓库根目录，默认从脚本位置向上找 sites/cloverphp.top")
    ap = argparse.ArgumentParser(description="www.cloverphp.top 巡检与推送（凭证已硬编码）")
    sub = ap.add_subparsers(dest="action")
    sub.add_parser("check", parents=[common], help="只读巡检：本地快照 + 线上技术门槛")
    sub.add_parser("push-baidu", parents=[common], help="百度普通收录 API 推送 7 条 URL")
    sub.add_parser("push-indexnow", parents=[common], help="必应 IndexNow 推送 7 条 URL")
    sub.add_parser("push", parents=[common], help="百度与必应各推一次")
    args = ap.parse_args()
    action = args.action or "check"

    rows: list = []
    if action == "check":
        local_snapshot(find_repo(args.repo), rows)
        online(rows)
    elif action == "push-baidu":
        push_baidu(rows)
    elif action == "push-indexnow":
        push_indexnow(rows)
    elif action == "push":
        push_baidu(rows)
        push_indexnow(rows)
    return emit(rows, args.json)


if __name__ == "__main__":
    raise SystemExit(main())
