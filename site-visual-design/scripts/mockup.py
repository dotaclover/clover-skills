#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mockup.py —— 设计稿落地三件套（成规格 → 出原型 → 查问题）

建站设计流水线里，出图之后不是直接写进 S1/S2，而是先出一版**可交互的 HTML 原型**，
客户在原型上看效果、改结构，确认了再落进主题。原型是中间产物，不是交付物。

三个子命令：

    scaffold   从规格 JSON 生成多页可交互原型（HTML + CSS + JS，无依赖、无构建）
    palette    从设计图采样主色，输出 CSS 变量并算 WCAG 对比度
    check      扫原型目录：资源缺失、占位符残留、配色对比度不达标

## 为什么要有 scaffold

手写六页 HTML 容易前后不一致：改了导航要动六个文件，配色改一次要全局搜。
规格 JSON 是唯一事实源，改规格重新生成，页面之间不会走样。

## 规格 JSON 长什么样

```json
{
  "name": "江南咖啡馆",
  "kicker": "江南西 · 手冲咖啡",
  "tagline": "街角的豆子，慢慢冲",
  "description": "一句话说清这是什么店",
  "nav": [{"label": "首页", "href": "index.html"}],
  "palette": {"paper": "#fbf7f1", "ink": "#7c4724", "body": "#6f5f50",
              "soft": "#7a6a5b", "brand": "#a05f30"},
  "pages": [
    {"slug": "index", "title": "首页", "blocks": [
      {"type": "hero", "kicker": "...", "title": "...", "lede": "...",
       "facts": ["..."], "actions": [{"label": "看看菜单", "href": "menu.html", "primary": true}],
       "image": "img/hero.jpg", "badge": "营业中"},
      {"type": "tiles", "title": "招牌与主营", "items": [
        {"img": "img/tile-1.jpg", "title": "手冲咖啡", "text": "...", "href": "menu.html"}]},
      {"type": "menu", "title": "菜单", "categories": ["全部", "手冲"], "items": [
        {"img": "img/m1.jpg", "name": "耶加雪菲", "desc": "...", "price": "38", "cat": "手冲"}]},
      {"type": "info", "title": "到店信息", "items": [{"label": "地址", "value": "..."}]},
      {"type": "faq", "title": "常见问题", "items": [{"q": "...", "a": "..."}]},
      {"type": "form", "title": "在线订位", "note": "...", "fields": [
        {"name": "customer_name", "label": "怎么称呼您", "type": "text", "required": true}]},
      {"type": "cta", "title": "...", "text": "...", "button": {"label": "...", "href": "..."}},
      {"type": "figures", "title": "...", "items": [{"num": "18", "label": "个座位"}]},
      {"type": "prose", "title": "...", "paragraphs": ["..."]}
    ]}
  ]
}
```

`blocks` 的顺序就是页面上的顺序。缺的字段不报错，按默认值渲染。
"""

import argparse
import html
import json
import re
import struct
import sys
import zlib
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(errors="replace")
        sys.stderr.reconfigure(errors="replace")
    except Exception:
        pass


# ---------------------------------------------------------------- 颜色工具

def hex_to_rgb(value):
    v = (value or "").strip().lstrip("#")
    if len(v) == 3:
        v = "".join(c * 2 for c in v)
    if len(v) != 6:
        return None
    try:
        return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return None


def rgb_to_hex(rgb):
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(c))) for c in rgb)


def relative_luminance(rgb):
    def ch(c):
        s = c / 255.0
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast_ratio(fg, bg):
    """WCAG 相对亮度对比度。任一色非法返回 None。"""
    a, b = hex_to_rgb(fg), hex_to_rgb(bg)
    if not a or not b:
        return None
    la, lb = relative_luminance(a), relative_luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def mix(hex_a, hex_b, ratio):
    """把 a 按 ratio 混向 b（ratio=0 全 a，1 全 b）。用于压深/提亮主色。"""
    a, b = hex_to_rgb(hex_a), hex_to_rgb(hex_b)
    if not a or not b:
        return hex_a
    return rgb_to_hex([a[i] + (b[i] - a[i]) * ratio for i in range(3)])


def darken_to_pass(brand, bg, target=4.5):
    """把主色压深（或提亮）到对 bg 的对比度达标，返回新色与实际对比度。

    按钮底色配白字最容易踩这条：肉眼看着舒服的 #a56537 只有 4.65:1，
    压到 #a05f30 才有 5.03:1。
    """
    best = brand
    best_ratio = contrast_ratio(brand, bg) or 0
    if best_ratio >= target:
        return brand, best_ratio
    for step in range(1, 21):
        cand = mix(brand, "#000000", step * 0.05)
        ratio = contrast_ratio(cand, bg) or 0
        if ratio > best_ratio:
            best, best_ratio = cand, ratio
        if ratio >= target:
            return cand, ratio
    return best, best_ratio


# ---------------------------------------------------------------- 采样

def _png_pixels(path, max_side=160):
    """纯标准库解 PNG，返回像素列表 [(r,g,b), ...]。非 PNG 或解码失败返回 None。"""
    raw = Path(path).read_bytes()
    if raw[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    pos = 8
    idat = b""
    width = height = bitdepth = colortype = None
    while pos + 8 <= len(raw):
        length = struct.unpack(">I", raw[pos:pos + 4])[0]
        ctype = raw[pos + 4:pos + 8]
        data = raw[pos + 8:pos + 8 + length]
        if ctype == b"IHDR":
            width, height, bitdepth, colortype = struct.unpack(">IIBB", data[:10])
        elif ctype == b"IDAT":
            idat += data
        elif ctype == b"IEND":
            break
        pos += 12 + length
    if not width or not height or bitdepth != 8:
        return None
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(colortype)
    if not channels:
        return None
    try:
        plain = zlib.decompress(idat)
    except zlib.error:
        return None
    stride = width * channels
    pixels = []
    prev = bytearray(stride)
    offset = 0
    step = max(1, min(width, height) // max_side)
    for y in range(height):
        if offset + 1 + stride > len(plain):
            break
        ft = plain[offset]
        line = bytearray(plain[offset + 1:offset + 1 + stride])
        offset += 1 + stride
        if ft == 1:
            for i in range(channels, stride):
                line[i] = (line[i] + line[i - channels]) & 0xFF
        elif ft == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif ft == 3:
            for i in range(stride):
                left = line[i - channels] if i >= channels else 0
                line[i] = (line[i] + ((left + prev[i]) >> 1)) & 0xFF
        elif ft == 4:
            for i in range(stride):
                a = line[i - channels] if i >= channels else 0
                b = prev[i]
                c = prev[i - channels] if i >= channels else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 0xFF
        if y % step == 0:
            for x in range(0, width, step):
                base = x * channels
                if channels >= 3:
                    pixels.append((line[base], line[base + 1], line[base + 2]))
                else:
                    pixels.append((line[base], line[base], line[base]))
        prev = line
    return pixels


def _pil_pixels(path, max_side=160):
    try:
        from PIL import Image
    except ImportError:
        return None
    img = Image.open(path).convert("RGB")
    img.thumbnail((max_side, max_side))
    # Pillow 10 起 getdata 有弃用警告；新版走 get_flattened_data
    getter = getattr(img, "get_flattened_data", None)
    return list(getter() if getter else img.getdata())


def sample_palette(image_path, count=5):
    """采样主色。返回 [(hex, 占比, 像素数), ...]，按占比降序。

    有 Pillow 就用 Pillow（JPEG 也能读）；没有就用纯标准库解 PNG。
    """
    path = Path(image_path)
    if not path.is_file():
        raise SystemExit("error: 找不到图片 %s" % path)
    pixels = _pil_pixels(path) or _png_pixels(path)
    if not pixels:
        raise SystemExit("error: 读不出像素（只支持 PNG 纯标准库解码，JPEG 需要 Pillow）")
    buckets = {}
    for r, g, b in pixels:
        # 量化到 5bit 一档，够用且能合并相近色
        key = (r // 32, g // 32, b // 32)
        buckets[key] = buckets.get(key, 0) + 1
    total = len(pixels)
    ranked = sorted(buckets.items(), key=lambda kv: kv[1], reverse=True)
    # 相邻色合并，避免出一堆肉眼一样的颜色
    merged = []
    for (r, g, b), n in ranked:
        hexv = rgb_to_hex((r * 32 + 16, g * 32 + 16, b * 32 + 16))
        if any(contrast_ratio(hexv, m[0]) is not None and contrast_ratio(hexv, m[0]) < 1.35 for m in merged):
            merged[-1] = (merged[-1][0], merged[-1][1] + n, merged[-1][2])
            continue
        merged.append((hexv, n, 0))
    result = []
    for hexv, n, _ in merged[:count]:
        result.append((hexv, round(n / float(total) * 100, 1), n))
    return result


# ---------------------------------------------------------------- 规格 → 原型

DEFAULT_PALETTE = {
    "paper": "#fbf7f1",
    "paper2": "#f3ece0",
    "ink": "#2b2622",
    "body": "#4a423a",
    "soft": "#7a6a5b",
    "line": "#e8ddcd",
    "brand": "#a05f30",
    "onbrand": "#fffdfa",
}

CSS_TEMPLATE = """/* {name} · 版式原型
   由 expert/skills/site-visual-design/scripts/mockup.py scaffold 生成，改规格重生成，别手改本文件。
   纯 HTML/CSS/JS，无构建、无依赖，file:// 双击能开。 */

:root {{
  --paper: {paper};
  --paper-2: {paper2};
  --ink: {ink};
  --body: {body};
  --soft: {soft};
  --line: {line};
  --brand: {brand};
  --on-brand: {onbrand};
  --s1: 4px; --s2: 8px; --s3: 12px; --s4: 16px; --s5: 24px; --s6: 32px; --s7: 48px; --s8: 64px;
  --gutter: 24px;
  --radius: 14px;
  --shadow: 0 10px 30px rgba(43, 38, 34, .10);
  --ease: cubic-bezier(.22, .61, .36, 1);
}}

* {{ box-sizing: border-box; }}
html {{ -webkit-text-size-adjust: 100%; }}
body {{
  margin: 0; background: var(--paper); color: var(--body);
  font: 16px/1.75 -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
        "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
}}
img {{ max-width: 100%; height: auto; display: block; }}
a {{ color: inherit; }}
h1, h2, h3 {{ color: var(--ink); line-height: 1.25; margin: 0 0 var(--s4); letter-spacing: -.01em; }}
h1 {{ font-size: clamp(30px, 5vw, 46px); font-weight: 800; }}
h2 {{ font-size: clamp(22px, 3vw, 30px); font-weight: 700; }}
h3 {{ font-size: 18px; font-weight: 700; }}
p {{ margin: 0 0 var(--s4); }}
.wrap {{ width: 100%; max-width: 1120px; margin: 0 auto; padding: 0 var(--gutter); }}
.skip {{ position: absolute; left: -9999px; }}
.skip:focus {{ left: var(--s3); top: var(--s3); z-index: 99; background: var(--ink); color: #fff;
  padding: var(--s2) var(--s3); border-radius: 8px; }}
:focus-visible {{ outline: 2px solid var(--brand); outline-offset: 3px; }}

/* 页头：吸顶 + 滚动后描边 */
.site-head {{ position: sticky; top: 0; z-index: 40; background: rgba(251, 247, 241, .92);
  backdrop-filter: blur(10px); border-bottom: 1px solid transparent; transition: border-color .25s var(--ease); }}
.site-head.is-stuck {{ border-bottom-color: var(--line); }}
.head-inner {{ display: flex; align-items: center; gap: var(--s5); min-height: 68px; }}
.brand {{ display: inline-flex; align-items: center; gap: 10px; color: var(--ink);
  font-weight: 800; font-size: 17px; text-decoration: none; }}
.brand-mark {{ display: inline-grid; place-items: center; width: 34px; height: 34px;
  border-radius: 10px; background: var(--brand); color: var(--on-brand); font-size: 16px; }}
.nav {{ display: flex; gap: var(--s5); margin-left: auto; }}
.nav a {{ text-decoration: none; color: var(--soft); font-size: 15px; padding: 6px 0;
  border-bottom: 2px solid transparent; }}
.nav a:hover, .nav a[aria-current="page"] {{ color: var(--ink); border-bottom-color: var(--brand); }}
.head-cta {{ margin-left: var(--s2); }}
.burger {{ display: none; margin-left: auto; width: 42px; height: 42px; border: 1px solid var(--line);
  border-radius: 10px; background: transparent; cursor: pointer; padding: 11px 9px; }}
.burger span {{ display: block; height: 2px; background: var(--ink); border-radius: 2px; margin: 4px 0;
  transition: transform .25s var(--ease), opacity .25s var(--ease); }}

/* 按钮 */
.btn {{ display: inline-flex; align-items: center; justify-content: center; gap: 8px;
  padding: 11px 20px; border-radius: 999px; text-decoration: none; font-weight: 600;
  font-size: 15px; border: 1px solid transparent; transition: transform .2s var(--ease), box-shadow .2s var(--ease); }}
.btn-primary {{ background: var(--brand); color: var(--on-brand); }}
.btn-primary:hover {{ transform: translateY(-1px); box-shadow: var(--shadow); }}
.btn-ghost {{ background: transparent; color: var(--ink); border-color: var(--line); }}
.btn-ghost:hover {{ border-color: var(--ink); }}
.btn[disabled] {{ opacity: .55; cursor: not-allowed; }}

/* 首屏 */
.hero {{ padding: var(--s8) 0 var(--s7); }}
.hero-grid {{ display: grid; grid-template-columns: 1.05fr .95fr; gap: var(--s7); align-items: center; }}
.kicker {{ display: inline-block; font-size: 13px; letter-spacing: .12em; color: var(--soft);
  text-transform: uppercase; margin-bottom: var(--s3); }}
.lede {{ font-size: 17px; color: var(--body); max-width: 46ch; }}
.hero-facts {{ list-style: none; padding: 0; margin: var(--s5) 0; display: flex; flex-wrap: wrap; gap: 10px; }}
.hero-facts li {{ font-size: 14px; color: var(--soft); background: var(--paper-2);
  border-radius: 999px; padding: 6px 12px; }}
.hero-actions {{ display: flex; flex-wrap: wrap; gap: var(--s3); }}
.hero-media {{ position: relative; }}
.hero-media img {{ width: 100%; aspect-ratio: 4/5; object-fit: cover; border-radius: var(--radius); }}
.hero-badge {{ position: absolute; left: 14px; bottom: 14px; background: var(--ink); color: #fff;
  font-size: 13px; padding: 6px 12px; border-radius: 999px; }}

/* 区块 */
.section {{ padding: var(--s8) 0; }}
.section.alt {{ background: var(--paper-2); }}
.page-head {{ padding: var(--s7) 0 var(--s5); }}
.sec-head {{ max-width: 640px; margin-bottom: var(--s6); }}
.sec-head p {{ color: var(--soft); margin: 0; }}

/* 图文砖 */
.tiles {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--s4); }}
.tile {{ display: block; text-decoration: none; background: #fff; border: 1px solid var(--line);
  border-radius: var(--radius); overflow: hidden; transition: transform .25s var(--ease), box-shadow .25s var(--ease); }}
.tile:hover {{ transform: translateY(-3px); box-shadow: var(--shadow); }}
.tile img {{ width: 100%; aspect-ratio: 1/1; object-fit: cover; }}
.tile-body {{ padding: var(--s4); }}
.tile-body h3 {{ margin-bottom: 6px; }}
.tile-body p {{ margin: 0; font-size: 14px; color: var(--soft); }}
.tile-more {{ display: inline-block; margin-top: 10px; font-size: 14px; color: var(--brand); font-weight: 600; }}

/* 菜单 */
.pills {{ display: flex; gap: var(--s2); flex-wrap: wrap; margin-bottom: var(--s5); }}
.pill {{ border: 1px solid var(--line); background: transparent; color: var(--soft); border-radius: 999px;
  padding: 7px 14px; font-size: 14px; cursor: pointer; white-space: nowrap; }}
.pill[aria-pressed="true"] {{ background: var(--brand); border-color: var(--brand); color: var(--on-brand); }}
.menu-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: var(--s4); }}
.dish {{ display: flex; gap: var(--s4); background: #fff; border: 1px solid var(--line);
  border-radius: var(--radius); padding: var(--s3); align-items: center; }}
.dish-img {{ width: 96px; flex: none; aspect-ratio: 1/1; border-radius: 10px; overflow: hidden; }}
.dish-img img {{ width: 100%; height: 100%; object-fit: cover; }}
.dish-body {{ min-width: 0; }}
.dish-body h3 {{ margin: 0 0 4px; font-size: 16px; }}
.dish-body p {{ margin: 0 0 6px; font-size: 14px; color: var(--soft); }}
.dish-price {{ color: var(--brand); font-weight: 700; }}

/* 信息表 */
.info-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--s4); }}
.info-card {{ background: #fff; border: 1px solid var(--line); border-radius: var(--radius); padding: var(--s5); }}
.info-card dt {{ font-size: 13px; color: var(--soft); margin-bottom: 6px; }}
.info-card dd {{ margin: 0; color: var(--ink); font-weight: 600; }}

/* 数字条 */
.figures {{ display: flex; flex-wrap: wrap; gap: var(--s6); }}
.figure-num {{ font-size: 34px; font-weight: 800; color: var(--brand); line-height: 1.1; }}
.figure-label {{ font-size: 14px; color: var(--soft); }}

/* FAQ */
.faq {{ border-top: 1px solid var(--line); }}
.faq details {{ border-bottom: 1px solid var(--line); padding: var(--s4) 0; }}
.faq summary {{ cursor: pointer; color: var(--ink); font-weight: 600; list-style: none;
  display: flex; justify-content: space-between; gap: var(--s4); }}
.faq summary::-webkit-details-marker {{ display: none; }}
.faq summary::after {{ content: "+"; color: var(--brand); font-weight: 700; }}
.faq details[open] summary::after {{ content: "−"; }}
.faq p {{ margin: var(--s3) 0 0; color: var(--soft); }}

/* CTA */
.cta-band {{ background: var(--paper-2); border-radius: var(--radius); padding: var(--s7); text-align: center; }}
.cta-band h2 {{ margin-bottom: var(--s3); }}

/* 表单 */
.form-card {{ background: #fff; border: 1px solid var(--line); border-radius: var(--radius);
  padding: var(--s6); max-width: 560px; }}
.form-row {{ margin-bottom: var(--s4); }}
.form-row label {{ display: block; font-size: 14px; color: var(--ink); margin-bottom: 6px; font-weight: 600; }}
.form-row input, .form-row select, .form-row textarea {{ width: 100%; padding: 11px 14px;
  border: 1px solid var(--line); border-radius: 999px; font: inherit; font-size: 15px;
  background: var(--paper); color: var(--body); }}
.form-row textarea {{ border-radius: var(--radius); min-height: 96px; resize: vertical; }}
.form-row input:focus, .form-row select:focus, .form-row textarea:focus {{
  outline: none; border-color: var(--brand); box-shadow: 0 0 0 3px rgba(160, 95, 48, .14); }}
.form-row.is-error input, .form-row.is-error select {{ border-color: #b3261e; }}
.form-error {{ display: none; color: #b3261e; font-size: 13px; margin-top: 6px; }}
.form-row.is-error .form-error {{ display: block; }}
.form-consent {{ display: flex; gap: 10px; align-items: flex-start; font-size: 14px; color: var(--soft); }}
.form-consent input {{ width: auto; margin-top: 4px; }}
.form-notice {{ text-align: center; padding: var(--s6) 0; }}
.form-notice.ok {{ color: var(--ink); }}
.form-notice.bad {{ color: #b3261e; }}

/* 页脚 */
.site-foot {{ background: var(--paper-2); border-top: 1px solid var(--line); padding: var(--s7) 0 var(--s5); margin-top: var(--s8); }}
.foot-grid {{ display: grid; grid-template-columns: 1.4fr 1fr 1fr; gap: var(--s6); }}
.foot-grid h3 {{ font-size: 15px; margin-bottom: var(--s3); }}
.foot-grid ul {{ list-style: none; padding: 0; margin: 0; }}
.foot-grid li {{ margin-bottom: 8px; font-size: 14px; }}
.foot-grid a {{ color: var(--soft); text-decoration: none; }}
.foot-grid a:hover {{ color: var(--brand); }}
.foot-note {{ margin-top: var(--s6); padding-top: var(--s4); border-top: 1px solid var(--line);
  font-size: 13px; color: var(--soft); display: flex; justify-content: space-between; gap: var(--s4); flex-wrap: wrap; }}

/* 渐入 */
.reveal {{ opacity: 0; transform: translateY(14px); }}
.reveal.in {{ opacity: 1; transform: none; transition: opacity .6s var(--ease), transform .6s var(--ease); }}
@media (prefers-reduced-motion: reduce) {{
  .reveal {{ opacity: 1; transform: none; }}
  * {{ transition-duration: .01ms !important; animation-duration: .01ms !important; }}
}}

/* 平板 */
@media (max-width: 900px) {{
  .hero-grid {{ grid-template-columns: 1fr; }}
  .hero-media img {{ aspect-ratio: 3/2; }}
  .tiles {{ grid-template-columns: repeat(2, 1fr); }}
  .menu-grid {{ grid-template-columns: 1fr; }}
  .info-grid {{ grid-template-columns: 1fr; }}
  .foot-grid {{ grid-template-columns: 1fr 1fr; }}
}}

/* 手机 */
@media (max-width: 760px) {{
  :root {{ --gutter: 16px; }}
  .nav {{ display: none; position: absolute; top: 68px; left: 0; right: 0; flex-direction: column;
    gap: 0; background: var(--paper); border-bottom: 1px solid var(--line); padding: var(--s3) var(--gutter) var(--s5); }}
  .nav.is-open {{ display: flex; }}
  .nav a {{ padding: 12px 0; border-bottom: 1px solid var(--line); }}
  .head-cta {{ display: none; }}
  .burger {{ display: block; }}
  .burger[aria-expanded="true"] span:nth-child(1) {{ transform: translateY(6px) rotate(45deg); }}
  .burger[aria-expanded="true"] span:nth-child(2) {{ opacity: 0; }}
  .burger[aria-expanded="true"] span:nth-child(3) {{ transform: translateY(-6px) rotate(-45deg); }}
  .tiles {{ grid-template-columns: 1fr; }}
  .foot-grid {{ grid-template-columns: 1fr; }}
  .section {{ padding: var(--s7) 0; }}
  .dish {{ flex-direction: row; }}
}}
"""

JS_TEMPLATE = """/* {name} · 版式原型交互
   由 expert/skills/site-visual-design/scripts/mockup.py scaffold 生成，改规格重生成，别手改本文件。
   无依赖，file:// 直接打开也能跑。 */

(function () {{
  "use strict";
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---------------------------------------------------------- 页头 --- */
  var head = document.getElementById("head");
  var burger = document.getElementById("burger");
  var nav = document.getElementById("nav");

  if (head) {{
    var onScroll = function () {{ head.classList.toggle("is-stuck", window.scrollY > 8); }};
    onScroll();
    window.addEventListener("scroll", onScroll, {{ passive: true }});
  }}

  if (burger && nav) {{
    var setNav = function (open) {{
      nav.classList.toggle("is-open", open);
      burger.setAttribute("aria-expanded", String(open));
      burger.setAttribute("aria-label", open ? "收起导航" : "展开导航");
    }};
    burger.addEventListener("click", function () {{
      setNav(burger.getAttribute("aria-expanded") !== "true");
    }});
    nav.addEventListener("click", function (e) {{
      if (e.target.closest("a")) setNav(false);
    }});
    document.addEventListener("keydown", function (e) {{
      if (e.key === "Escape" && nav.classList.contains("is-open")) {{ setNav(false); burger.focus(); }}
    }});
  }}

  /* ---------------------------------------------------------- 渐入 --- */
  var reveals = document.querySelectorAll(".reveal");
  if (reveals.length) {{
    if (reduce || !("IntersectionObserver" in window)) {{
      reveals.forEach(function (el) {{ el.classList.add("in"); }});
    }} else {{
      var io = new IntersectionObserver(function (entries) {{
        entries.forEach(function (en) {{
          if (en.isIntersecting) {{ en.target.classList.add("in"); io.unobserve(en.target); }}
        }});
      }}, {{ rootMargin: "0px 0px -8% 0px" }});
      reveals.forEach(function (el) {{ io.observe(el); }});
    }}
  }}

  /* -------------------------------------------------------- 菜单筛选 --- */
  var pills = document.querySelectorAll(".pill");
  var dishes = document.querySelectorAll(".menu-grid .dish");
  if (pills.length && dishes.length) {{
    pills.forEach(function (pill) {{
      pill.addEventListener("click", function () {{
        var filter = pill.getAttribute("data-filter");
        pills.forEach(function (p) {{ p.setAttribute("aria-pressed", String(p === pill)); }});
        dishes.forEach(function (dish) {{
          var show = filter === "all" || dish.getAttribute("data-cat") === filter;
          dish.hidden = !show;
        }});
      }});
    }});
  }}

  /* ---------------------------------------------------------- 表单 --- */
  var form = document.querySelector(".booking-form");
  if (form) {{
    form.addEventListener("submit", function (e) {{
      e.preventDefault();
      var ok = true;
      form.querySelectorAll("[required]").forEach(function (field) {{
        var row = field.closest(".form-row");
        var bad = !String(field.value || "").trim();
        if (row) row.classList.toggle("is-error", bad);
        if (bad) ok = false;
      }});
      var consent = form.querySelector('input[name="consent"]');
      if (consent && !consent.checked) ok = false;
      if (!ok) {{
        var first = form.querySelector(".form-row.is-error input, .form-row.is-error select");
        if (first) first.focus();
        return;
      }}
      var card = form.parentNode;
      card.innerHTML = '<div class="form-notice ok"><h3>已收到</h3>' +
        '<p>原型演示：信息未发送、未保存，不构成真实预约。</p>' +
        '<button class="btn btn-ghost" type="button" id="again">再填一次</button></div>';
      var again = document.getElementById("again");
      if (again) again.addEventListener("click", function () {{ location.reload(); }});
    }});
  }}
}})();
"""


def esc(value):
    return html.escape(str(value if value is not None else ""))


def attr(value):
    return html.escape(str(value if value is not None else ""), quote=True)


def block_html(b, page_slug, as_h1=False):
    """把一个 block 渲染成 HTML 片段。

    as_h1=True 时区块标题渲染成 h1（页面第一个有标题的区块用），
    保证每个页面有且只有一个 H1，且不会出现「页头标题 + 区块标题」重复。
    """
    kind = (b.get("type") or "").strip()
    H = "h1" if as_h1 else "h2"

    if kind == "pagehead":
        lead = '<p style="color:var(--soft);margin:0">%s</p>' % esc(b["lead"]) if b.get("lead") else ""
        return ('<section class="page-head"><div class="wrap"><h1>%s</h1>%s</div></section>'
                % (esc(b.get("title")), lead))

    if kind == "hero":
        facts = "".join("<li>%s</li>" % esc(f) for f in (b.get("facts") or []))
        actions = ""
        for a in (b.get("actions") or []):
            cls = "btn btn-primary" if a.get("primary") else "btn btn-ghost"
            actions += '<a class="%s" href="%s">%s</a>' % (cls, attr(a.get("href", "#")), esc(a.get("label")))
        media = ""
        if b.get("image"):
            badge = '<span class="hero-badge">%s</span>' % esc(b["badge"]) if b.get("badge") else ""
            media = ('<div class="hero-media"><img src="%s" alt="%s">%s</div>'
                     % (attr(b["image"]), attr(b.get("alt", b.get("title", ""))), badge))
        return ('<section class="hero"><div class="wrap hero-grid"><div class="hero-copy">'
                '<span class="kicker">%s</span><h1>%s</h1><p class="lede">%s</p>'
                '<ul class="hero-facts">%s</ul><div class="hero-actions">%s</div></div>%s</div></section>'
                % (esc(b.get("kicker")), esc(b.get("title")), esc(b.get("lede")), facts, actions, media))

    if kind == "tiles":
        items = ""
        for it in (b.get("items") or []):
            img = ('<img src="%s" alt="%s">' % (attr(it.get("img")), attr(it.get("title")))
                   if it.get("img") else "")
            more = '<span class="tile-more">%s →</span>' % esc(it.get("more", "看详情")) if it.get("href") else ""
            items += ('<a class="tile" href="%s">%s<div class="tile-body"><h3>%s</h3><p>%s</p>%s</div></a>'
                      % (attr(it.get("href", "#")), img, esc(it.get("title")), esc(it.get("text")), more))
        head = ('<div class="sec-head"><%s>%s</%s><p>%s</p></div>' % (H, esc(b.get("title")), H, esc(b.get("lead")))
                if b.get("title") else "")
        return '<section class="section"><div class="wrap">%s<div class="tiles">%s</div></div></section>' % (head, items)

    if kind == "menu":
        cats = b.get("categories") or []
        pills = ""
        for i, c in enumerate(cats):
            key = "all" if i == 0 else str(c)
            pressed = "true" if i == 0 else "false"
            pills += '<button class="pill" type="button" data-filter="%s" aria-pressed="%s">%s</button>' % (
                attr(key), pressed, esc(c))
        items = ""
        for it in (b.get("items") or []):
            img = ('<img src="%s" alt="%s">' % (attr(it.get("img")), attr(it.get("name")))
                   if it.get("img") else "")
            items += ('<article class="dish" data-cat="%s"><div class="dish-img">%s</div>'
                      '<div class="dish-body"><h3>%s</h3><p>%s</p><span class="dish-price">%s</span></div></article>'
                      % (attr(it.get("cat", "")), img, esc(it.get("name")), esc(it.get("desc")),
                         esc(it.get("price", ""))))
        head = ('<div class="sec-head"><%s>%s</%s><p>%s</p></div>' % (H, esc(b.get("title")), H, esc(b.get("lead")))
                if b.get("title") else "")
        return ('<section class="section"><div class="wrap">%s<div class="pills">%s</div>'
                '<div class="menu-grid">%s</div></div></section>' % (head, pills, items))

    if kind == "info":
        cards = ""
        for it in (b.get("items") or []):
            cards += ('<dl class="info-card"><dt>%s</dt><dd>%s</dd></dl>'
                      % (esc(it.get("label")), esc(it.get("value"))))
        head = ('<div class="sec-head"><%s>%s</%s><p>%s</p></div>' % (H, esc(b.get("title")), H, esc(b.get("lead")))
                if b.get("title") else "")
        return '<section class="section alt"><div class="wrap">%s<div class="info-grid">%s</div></div></section>' % (head, cards)

    if kind == "figures":
        figs = ""
        for it in (b.get("items") or []):
            figs += ('<div class="figure"><div class="figure-num">%s</div>'
                     '<div class="figure-label">%s</div></div>' % (esc(it.get("num")), esc(it.get("label"))))
        head = ('<div class="sec-head"><%s>%s</%s><p>%s</p></div>' % (H, esc(b.get("title")), H, esc(b.get("lead")))
                if b.get("title") else "")
        return '<section class="section"><div class="wrap">%s<div class="figures">%s</div></div></section>' % (head, figs)

    if kind == "faq":
        rows = ""
        for it in (b.get("items") or []):
            rows += ('<details><summary>%s</summary><p>%s</p></details>'
                     % (esc(it.get("q")), esc(it.get("a"))))
        head = ('<div class="sec-head"><%s>%s</%s><p>%s</p></div>' % (H, esc(b.get("title")), H, esc(b.get("lead")))
                if b.get("title") else "")
        more = ('<p style="margin-top:24px"><a href="%s">%s →</a></p>'
                % (attr(b.get("moreHref", "#")), esc(b.get("moreText", "还有别的问题"))) if b.get("moreHref") else "")
        return '<section class="section alt"><div class="wrap">%s<div class="faq">%s</div>%s</div></section>' % (head, rows, more)

    if kind == "form":
        fields = ""
        for f in (b.get("fields") or []):
            ftype = f.get("type", "text")
            req = " required" if f.get("required") else ""
            if ftype == "select":
                opts = "".join('<option value="%s">%s</option>' % (attr(o), esc(o)) for o in (f.get("options") or []))
                control = '<select name="%s"%s>%s</select>' % (attr(f.get("name")), req, opts)
            elif ftype == "textarea":
                control = '<textarea name="%s"%s placeholder="%s"></textarea>' % (
                    attr(f.get("name")), req, attr(f.get("placeholder", "")))
            else:
                control = '<input type="%s" name="%s"%s placeholder="%s">' % (
                    attr(ftype), attr(f.get("name")), req, attr(f.get("placeholder", "")))
            err = '<span class="form-error">%s</span>' % esc(f.get("error", "这一项要填"))
            fields += ('<p class="form-row"><label for="f-%s">%s</label>%s%s</p>'
                       % (attr(f.get("name")), esc(f.get("label")), control, err))
        consent = ('<p class="form-row form-consent"><input type="checkbox" name="consent" required>'
                   '<span>%s</span></p>' % esc(b.get("consent", "同意店家联系我"))) if b.get("consent") else ""
        note = '<p style="color:var(--soft);font-size:14px">%s</p>' % esc(b["note"]) if b.get("note") else ""
        head = ('<div class="sec-head"><%s>%s</%s><p>%s</p></div>' % (H, esc(b.get("title")), H, esc(b.get("lead")))
                if b.get("title") else "")
        return ('<section class="section"><div class="wrap">%s<div class="form-card">%s'
                '<form class="booking-form" novalidate>%s%s'
                '<button class="btn btn-primary" type="submit">%s</button></form></div></div></section>'
                % (head, note, fields, consent, esc(b.get("submit", "提交"))))

    if kind == "cta":
        btn = b.get("button") or {}
        return ('<section class="section"><div class="wrap"><div class="cta-band"><%s>%s</%s><p>%s</p>'
                '<a class="btn btn-primary" href="%s">%s</a></div></div></section>'
                % (H, esc(b.get("title")), H, esc(b.get("text")),
                   attr(btn.get("href", "#")), esc(btn.get("label"))))

    if kind == "prose":
        paras = "".join("<p>%s</p>" % esc(p) for p in (b.get("paragraphs") or []))
        head = '<%s>%s</%s>' % (H, esc(b["title"]), H) if b.get("title") else ""
        return '<section class="section"><div class="wrap">%s%s</div></section>' % (head, paras)

    return ""


def render_page(spec, page, nav_html, foot_html):
    slug = page.get("slug", "index")
    body = ""
    h1_done = False
    for b in (page.get("blocks") or []):
        # 页面第一个带标题的区块承担 H1，避免「自动页头 + 区块标题」重复两遍标题
        is_first_title = (not h1_done) and bool(b.get("title")) and b.get("type") != "hero"
        body += block_html(b, slug, as_h1=is_first_title)
        if is_first_title or b.get("type") == "hero":
            h1_done = True

    # 整页都没有标题时，用页面名补一个 H1，保证每页恰好一个
    if "<h1" not in body:
        body = ('<section class="page-head"><div class="wrap"><h1>%s</h1></div></section>'
                % esc(page.get("title") or spec.get("name", ""))) + body

    title = "%s · %s" % (page.get("title", ""), spec.get("name", "")) if page.get("title") else spec.get("name", "")
    desc = spec.get("description", "")
    return """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%s</title>
<meta name="description" content="%s">
<link rel="stylesheet" href="style.css">
</head>
<body data-page="%s">
<a class="skip" href="#main">跳到正文</a>
%s
<main id="main">
%s
</main>
%s
<script src="app.js"></script>
</body>
</html>
""" % (esc(title), esc(desc), attr(slug), nav_html, body, foot_html)


def render_nav(spec, current):
    links = ""
    for item in (spec.get("nav") or []):
        cur = ' aria-current="page"' if item.get("href") == current else ""
        links += '<a href="%s"%s>%s</a>' % (attr(item.get("href", "#")), cur, esc(item.get("label")))
    cta = ""
    if spec.get("navCta"):
        cta = '<a class="btn btn-primary head-cta" href="%s">%s</a>' % (
            attr(spec["navCta"].get("href", "#")), esc(spec["navCta"].get("label")))
    return """<header class="site-head" id="head">
  <div class="wrap head-inner">
    <a class="brand" href="index.html"><span class="brand-mark" aria-hidden="true">%s</span>%s</a>
    <nav class="nav" id="nav" aria-label="主导航">%s</nav>
    %s
    <button class="burger" id="burger" aria-label="展开导航" aria-expanded="false" aria-controls="nav">
      <span></span><span></span><span></span>
    </button>
  </div>
</header>""" % (esc((spec.get("name") or "·")[:1]), esc(spec.get("name", "")), links, cta)


def render_foot(spec):
    cols = ""
    for col in (spec.get("footer") or []):
        links = "".join('<li><a href="%s">%s</a></li>' % (attr(i.get("href", "#")), esc(i.get("label")))
                        for i in (col.get("items") or []))
        cols += ('<div><h3>%s</h3><ul>%s</ul></div>' % (esc(col.get("title")), links))
    note = spec.get("footNote", "")
    return """<footer class="site-foot">
  <div class="wrap">
    <div class="foot-grid">
      <div><h3>%s</h3><p style="color:var(--soft);font-size:14px;max-width:34ch">%s</p></div>
      %s
    </div>
    <div class="foot-note"><span>%s</span><span>%s</span></div>
  </div>
</footer>""" % (esc(spec.get("name", "")), esc(spec.get("lead", "")), cols,
                esc(note), esc(spec.get("copyright", "")))


def cmd_scaffold(args):
    spec_path = Path(args.spec)
    if not spec_path.is_file():
        raise SystemExit("error: 找不到规格文件 %s" % spec_path)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))

    palette = dict(DEFAULT_PALETTE)
    palette.update(spec.get("palette") or {})

    # 主色对白字不达标就压深，别让按钮踩 WCAG AA
    fixed = []
    on_brand = palette.get("onbrand", "#fffdfa")
    ratio = contrast_ratio(palette.get("brand"), on_brand)
    if ratio is not None and ratio < 4.5:
        new_brand, new_ratio = darken_to_pass(palette["brand"], on_brand, 4.5)
        fixed.append("brand %s → %s（白字对比度 %.2f → %.2f）"
                     % (palette["brand"], new_brand, ratio, new_ratio))
        palette["brand"] = new_brand

    outdir = Path(args.out)
    if outdir.exists():
        raise SystemExit("error: 输出目录已存在，请选择新的 --out：%s" % outdir)
    slugs = [page.get("slug", "index") for page in (spec.get("pages") or [])]
    if any(not re.fullmatch(r"[A-Za-z0-9_-]+", str(slug)) for slug in slugs):
        raise SystemExit("error: slug 只能含字母、数字、下划线或连字符")
    if len(slugs) != len(set(slugs)):
        raise SystemExit("error: 页面 slug 重复")
    outdir.mkdir(parents=True, exist_ok=False)

    # 图片目录：出图结果落在哪，就把 img/ 指过去。规格里写 img/hero.jpg，
    # 实际图片在别处时用 --img-dir 指定，生成后图片会被拷进原型的 img/。
    img_src = Path(args.img_dir) if args.img_dir else None
    if img_src and not img_src.is_dir():
        raise SystemExit("error: --img-dir 指向的目录不存在：%s" % img_src)
    copied = []
    if img_src:
        target_img = outdir / "img"
        target_img.mkdir(parents=True, exist_ok=True)
        for src in sorted(img_src.iterdir()):
            if src.suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"):
                continue
            (target_img / src.name).write_bytes(src.read_bytes())
            copied.append(src.name)

    name = spec.get("name", "站点")
    # 模板里 {name} 与 {{...}}（CSS/JS 的字面花括号）都要正确还原
    fmt = dict(palette)
    fmt["name"] = name
    css = CSS_TEMPLATE.format(**fmt)
    js = JS_TEMPLATE.format(**fmt)
    (outdir / "style.css").write_text(css, encoding="utf-8")
    (outdir / "app.js").write_text(js, encoding="utf-8")

    written = []
    for page in (spec.get("pages") or []):
        slug = page.get("slug", "index")
        filename = "index.html" if slug == "index" else "%s.html" % slug
        nav_html = render_nav(spec, filename)
        foot_html = render_foot(spec)
        (outdir / filename).write_text(render_page(spec, page, nav_html, foot_html), encoding="utf-8")
        written.append(filename)

    report = {"out_dir": str(outdir), "pages": written,
              "palette": palette, "palette_fixed": fixed, "images_copied": copied}
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("原型已生成：%s" % outdir)
        for f in written:
            print("  %s" % f)
        print("  style.css")
        print("  app.js")
        if copied:
            print("  img/（%d 张）" % len(copied))
        if fixed:
            print("\n配色调整：")
            for f in fixed:
                print("  %s" % f)
        print("\n双击 index.html 就能看。改设计改规格 JSON，重新生成，别手改产物。")


def cmd_palette(args):
    colors = sample_palette(args.image, args.count)
    paper = args.paper
    rows = []
    for hexv, pct, n in colors:
        r_on_paper = contrast_ratio(hexv, paper)
        r_on_white = contrast_ratio(hexv, "#ffffff")
        rows.append({
            "color": hexv,
            "percent": pct,
            "contrast_on_paper": round(r_on_paper, 2) if r_on_paper else None,
            "contrast_on_white": round(r_on_white, 2) if r_on_white else None,
            "as_text_ok": bool(r_on_paper and r_on_paper >= 4.5),
        })
    if args.json:
        print(json.dumps({"image": args.image, "paper": paper, "colors": rows}, ensure_ascii=False, indent=2))
        return

    print("图：%s（底色参考 %s）" % (args.image, paper))
    print("")
    print("%-10s %-8s %-14s %-14s %s" % ("颜色", "占比", "配底色对比度", "配白对比度", "可作正文"))
    for r in rows:
        print("%-10s %-7s%% %-14s %-14s %s" % (
            r["color"], r["percent"], r["contrast_on_paper"], r["contrast_on_white"],
            "可" if r["as_text_ok"] else "不可"))
    print("")
    print("正文要 4.5:1，大字 3:1。配色先定 paper 与 brand 两个，其余从中挑。")
    dark = colors[0][0] if colors else "#000000"
    fixed, ratio = darken_to_pass(dark, "#ffffff", 4.5)
    if ratio < 4.5:
        print("提醒：最深的色 %s 配白字只有 %.2f:1，按钮底色要压深到 %s（%.2f:1）。"
              % (dark, ratio, fixed, ratio))


def cmd_check(args):
    root = Path(args.dir)
    if not root.is_dir():
        raise SystemExit("error: 目录不存在 %s" % root)

    problems = []
    notes = []
    html_files = sorted(root.glob("*.html"))
    if not html_files:
        problems.append("目录里没有 HTML，原型没生成？")

    # 1. 资源引用
    for hf in html_files:
        text = hf.read_text(encoding="utf-8")
        for m in re.finditer(r'(?:src|href)="([^"]+)"', text):
            ref = m.group(1)
            if ref.startswith(("http://", "https://", "#", "data:", "mailto:", "tel:", "//")):
                continue
            target = (root / ref.split("#")[0]).resolve()
            if not target.is_file():
                problems.append("%s 引用了不存在的文件：%s" % (hf.name, ref))

    # 2. 占位符残留
    for hf in html_files:
        text = hf.read_text(encoding="utf-8")
        for token in ("{{", "}}", "【", "TODO"):
            if token in text:
                problems.append("%s 里还有占位符 %s" % (hf.name, token))

    # 3. 配色对比度
    css_path = root / "style.css"
    if css_path.is_file():
        css = css_path.read_text(encoding="utf-8")
        vars_found = dict(re.findall(r"--([a-z0-9-]+):\s*(#[0-9a-fA-F]{3,6})\s*;", css))
        paper = vars_found.get("paper", "#ffffff")
        onbrand = vars_found.get("onbrand", "#ffffff")
        ink = vars_found.get("ink")
        brand = vars_found.get("brand")
        body = vars_found.get("body")
        checks = [
            ("brand 按钮底色 vs 白字", brand, onbrand, 4.5),
            ("ink 标题 vs 底色", ink, paper, 4.5),
            ("body 正文 vs 底色", body, paper, 4.5),
        ]
        for label, fg, bg, need in checks:
            if not fg or not bg:
                continue
            r = contrast_ratio(fg, bg)
            if r is None:
                problems.append("%s 的颜色值非法" % label)
            elif r < need:
                problems.append("%s 对比度 %.2f:1，低于 AA 要求 %.1f:1" % (label, r, need))
            else:
                notes.append("%s %.2f:1 通过" % (label, r))
    else:
        problems.append("缺 style.css")

    # 4. 基本结构
    for hf in html_files:
        text = hf.read_text(encoding="utf-8")
        if "<h1" not in text:
            problems.append("%s 没有 H1" % hf.name)
        if text.count("<h1") > 1:
            problems.append("%s 有多个 H1（一个页面只留一个）" % hf.name)
        if "<title>" not in text:
            problems.append("%s 缺 title" % hf.name)
        if 'name="viewport"' not in text:
            problems.append("%s 缺 viewport meta（手机会跑版）" % hf.name)

    print("原型体检：%s（%d 页）" % (root, len(html_files)))
    for n in notes:
        print("  [OK] %s" % n)
    if problems:
        print("")
        for p in problems:
            print("  [!!] %s" % p)
        return 1
    print("\n没有问题。")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="mockup.py", description="设计稿落地：出原型、采配色、查问题")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("scaffold", help="从规格 JSON 生成多页原型")
    p.add_argument("--spec", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--img-dir", help="出图结果目录，生成时拷进原型的 img/")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=lambda a: cmd_scaffold(a) or 0)

    p = sub.add_parser("palette", help="从设计图采样主色并算对比度")
    p.add_argument("--image", required=True)
    p.add_argument("--count", type=int, default=5)
    p.add_argument("--paper", default="#ffffff", help="底色参考，算对比度用")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_palette)

    p = sub.add_parser("check", help="扫原型目录")
    p.add_argument("--dir", required=True)
    p.set_defaults(func=cmd_check)

    args = ap.parse_args(argv)
    sys.exit(args.func(args) or 0)


if __name__ == "__main__":
    main()
