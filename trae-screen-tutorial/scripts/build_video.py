# -*- coding: utf-8 -*-
"""决策复盘日记 · EP02 / EP03：

    EP02 改界面      python buildbuild.py --part 2
    EP03 写代码      python buildbuild.py --part 3
    python buildbuild.py --part 2 --preview   只出静帧

截图按长图滚动播放，滚动范围首尾相接，整段对话不重复不遗漏。
"""
import asyncio
import hashlib
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path

import edge_tts
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path.cwd()   # 产物落在调用时的项目目录，不污染技能本体
OUT = ROOT / "build"
ASSETS = OUT / "assets"
AUD = OUT / "audio"
SLI = OUT / "slides"
PARTS = OUT / "parts"

W, H, FPS = 1080, 1920, 30
VOICE, RATE = "zh-CN-YunxiNeural", "+8%"

SERIES = "Trae课程100课"

# 品牌素材随技能打包，即插即用；可用环境变量 WB_STAGE_BG / WB_AVATAR 覆盖
SKILL_DIR = Path(__file__).resolve().parent.parent
WB_BG = Path(os.environ.get("WB_STAGE_BG", str(SKILL_DIR / "assets" / "stage-bg.png")))
WB_AVATAR = Path(os.environ.get("WB_AVATAR", str(SKILL_DIR / "assets" / "avatar.jpg")))

# 舞台几何（底图 1440x2560 缩到 1080x1920，比例 0.75）
PANEL = (56, 1000, 968, 490)      # 内容舞台：媒体/文字区（底部留给 cap）
TITLE_CY = 480                    # 标题条纵向中心
EP_X = 968                        # EP 胶囊右锚（留出右侧留白）
SUB_CY = 1755                     # 口播字幕落进底部字幕条
CAP_Y0 = 1500                     # 结论字幕起点
AVATAR_CX, AVATAR_CY, AVATAR_D = 540, 237, 330
DEMO_Y = 430                      # 真机演示：全宽截图纵向起点

# WorkBuddy 方案2 配色：奶白底 + 深色字 + 蓝强调
C_TITLE = (28, 34, 50)
C_TEXT = (28, 34, 50)
C_DIM = (90, 110, 140)
C_MUTED = (90, 110, 140)
C_ACCENT = (48, 110, 190)
CREAM = (251, 245, 230)          # 内容卡奶油色（与底图一致）
C_LINE = (46, 59, 46)
C_BORDER = (46, 60, 78)

F_BOLD = r"C:\Windows\Fonts\msyhbd.ttc"
F_REG = r"C:\Windows\Fonts\msyh.ttc"

SHOT = ASSETS / "gitee.png"


def cn(text):
    """中文排版：汉字与字母/数字之间不留空格。"""
    cjk = r"[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]"
    text = re.sub(rf"(?<={cjk}) +", "", text)
    text = re.sub(rf" +(?={cjk})", "", text)
    return text


def make_promo(out):
    """开源推广卡：仓库截图 + 圈出 star / fork。"""
    T = 960
    im = Image.new("RGB", (T, 1200), (0, 0, 0))
    d = ImageDraw.Draw(im)

    f1 = ImageFont.truetype(F_BOLD, 76)
    t1 = "代码已开源"
    d.text(((T - d.textbbox((0, 0), t1, font=f1)[2]) // 2, 74), t1, font=f1, fill=C_TEXT)

    url = "gitee.com/clover/trae-decision-recorder"
    size = 46
    f2 = ImageFont.truetype(F_BOLD, size)
    while d.textbbox((0, 0), url, font=f2)[2] > 900 and size > 24:
        size -= 2
        f2 = ImageFont.truetype(F_BOLD, size)
    d.text(((T - d.textbbox((0, 0), url, font=f2)[2]) // 2, 188), url, font=f2, fill=C_ACCENT)

    shot = Image.open(SHOT).convert("RGB")
    k = T / shot.width
    head = shot.crop((0, 0, shot.width, 1010)).resize((T, int(1010 * k)), Image.LANCZOS)
    im.paste(head, (0, 272))
    d.rounded_rectangle([int(2650 * k), 272 + int(146 * k),
                         int(3012 * k), 272 + int(238 * k)],
                        radius=8, outline=C_ACCENT, width=4)

    ins = shot.crop((2600, 145, 3056, 245)).resize((912, 200), Image.LANCZOS)
    im.paste(ins, (24, 600))
    for x0, x1 in ((2680, 2827), (2835, 2985)):
        d.rounded_rectangle([24 + (x0 - 2600) * 2 - 12, 628,
                             24 + (x1 - 2600) * 2 + 12, 776],
                            radius=16, outline=C_ACCENT, width=6)

    f3 = ImageFont.truetype(F_BOLD, 60)
    t3 = "点个star，fork来玩"
    d.text(((T - d.textbbox((0, 0), t3, font=f3)[2]) // 2, 846), t3, font=f3, fill=C_TEXT)
    f4 = ImageFont.truetype(F_REG, 34)
    t4 = "克隆下来，用开发者工具导入就能跑"
    d.text(((T - d.textbbox((0, 0), t4, font=f4)[2]) // 2, 946), t4, font=f4, fill=C_DIM)
    im.save(out)
    return out

# 长截图里的对话分段（每段从用户提问起，到下一段提问前）
SEC_PROTO = (1588, 5128)      # 原型阶段：MVP 要求 → 复盘选项简化
SEC_F1 = (5128, 6391)         # 第一改：太复杂，砍类型
SEC_F2 = (6391, 7586)         # 第二改：tab 职责拆开
SEC_F3 = (7586, 10096)        # 第三改：文案换成人话
SEC_CODE = (10096, 11699)     # 写代码
SEC_TUNE = (11699, 14895)     # 图标 → 清示例数据 → 首次提交

HOLD = {"a01": 1.0, "a02a": 1.6, "a02b": 1.6, "a02c": 1.6, "a03a": 1.4,
        "a04": 1.4, "a05a": 1.4, "a06": 2.4, "a07": 3.0}


def run(cmd):
    subprocess.run([str(c) for c in cmd], check=True)


def probe(p):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", str(p)], capture_output=True, text=True)
    return float(out.stdout.strip())


def tts(name, text):
    key = hashlib.sha1((VOICE + RATE + text).encode()).hexdigest()[:10]
    out = AUD / f"{name}_{key}.mp3"
    if not out.exists():
        tmp = out.with_suffix(".part")
        asyncio.run(edge_tts.Communicate(text, VOICE, rate=RATE).save(str(tmp)))
        tmp.rename(out)
    return out


def bg(with_avatar=True):
    """WorkBuddy 讲解台底图；头像仅 PPT 卡显示。"""
    im = Image.open(WB_BG).convert("RGB").resize((W, H), Image.LANCZOS).convert("RGBA")
    if with_avatar:
        av = Image.open(WB_AVATAR).convert("RGBA").resize((AVATAR_D, AVATAR_D), Image.LANCZOS)
        mask = Image.new("L", (AVATAR_D, AVATAR_D), 0)
        ImageDraw.Draw(mask).ellipse([6, 6, AVATAR_D - 6, AVATAR_D - 6], fill=255)
        im.paste(av, (AVATAR_CX - AVATAR_D // 2, AVATAR_CY - AVATAR_D // 2), mask)
    return im


def demo_bg():
    """真机演示底：品牌深蓝竖向渐变，干净利落。"""
    top, bot = (16, 24, 38), (6, 9, 14)
    im = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(im)
    for y in range(H):
        t = y / (H - 1)
        d.line([(0, y), (W, y)],
               fill=tuple(int(top[k] + (bot[k] - top[k]) * t) for k in range(3)))
    return im.convert("RGBA")


def star4(cx, cy, r):
    pts = []
    for k in range(8):
        ang = math.pi / 4 * k - math.pi / 2
        rr = r if k % 2 == 0 else r * 0.40
        pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
    return pts


def deco_icons(d, cy):
    """PPT 卡上两个小图标点缀：代码 </> + AI 星芒。"""
    size, gap = 58, 30
    x0 = W // 2 - (size * 2 + gap) // 2
    for i in range(2):
        bx = x0 + i * (size + gap)
        d.rounded_rectangle([bx, cy, bx + size, cy + size], radius=16,
                            fill=(255, 253, 246), outline=C_ACCENT, width=3)
        cx, cc = bx + size // 2, cy + size // 2
        if i == 0:
            f = ImageFont.truetype(F_BOLD, 24)
            d.text((cx, cc), "</>", font=f, fill=C_ACCENT, anchor="mm")
        else:
            d.polygon(star4(cx, cc, 20), fill=C_ACCENT)


def endcard(b):
    """WorkBuddy 式干净收尾卡：浅灰底 + 居中大头像 + 搜索添加/AI从零开始。"""
    im = Image.new("RGB", (W, H), (243, 246, 250))
    cx, cy, dia = W // 2, 600, 500
    d = ImageDraw.Draw(im)
    d.ellipse([cx - dia // 2 - 10, cy - dia // 2 - 10,
               cx + dia // 2 + 10, cy + dia // 2 + 10],
              outline=(205, 212, 224), width=5)
    av = Image.open(WB_AVATAR).convert("RGBA").resize((dia, dia), Image.LANCZOS)
    mask = Image.new("L", (dia, dia), 0)
    ImageDraw.Draw(mask).ellipse([6, 6, dia - 6, dia - 6], fill=255)
    im.paste(av, (cx - dia // 2, cy - dia // 2), mask)
    d = ImageDraw.Draw(im)
    lines = b.get("panel", [])
    ys = [920, 995, 1135]
    for i, line in enumerate(lines[:3]):
        t = cn(line)
        if i == 1:
            size = 92
            fill = C_ACCENT
            f = ImageFont.truetype(F_BOLD, size)
            while d.textbbox((0, 0), t, font=f)[2] > 960 and size > 48:
                size -= 2
                f = ImageFont.truetype(F_BOLD, size)
        else:
            size = 40 if i == 0 else 36
            fill = C_DIM
            f = ImageFont.truetype(F_BOLD if i == 0 else F_REG, size)
            while d.textbbox((0, 0), t, font=f)[2] > 960 and size > 22:
                size -= 2
                f = ImageFont.truetype(F_BOLD if i == 0 else F_REG, size)
        wl = d.textbbox((0, 0), t, font=f)[2]
        d.text(((W - wl) // 2, ys[i]), t, font=f, fill=fill)
    return im


def demo_scene(b):
    """真机演示：模糊压暗底 + 顶部蓝色标题条 + 结论行（截图由 render 全宽叠入）。"""
    im = demo_bg()
    d = ImageDraw.Draw(im)
    title = cn(b.get("title", ""))
    f_t = ImageFont.truetype(F_BOLD, 44)
    while d.textbbox((0, 0), title, font=f_t)[2] > 900 and f_t.size > 26:
        f_t = ImageFont.truetype(F_BOLD, f_t.size - 2)
    tw = d.textbbox((0, 0), title, font=f_t)[2]
    pad, y0 = 28, 300
    d.rounded_rectangle([56, y0, 56 + tw + pad * 2, y0 + 78], radius=22, fill=C_ACCENT)
    d.text((56 + pad, y0 + 39), title, font=f_t, fill=(255, 255, 255), anchor="lm")

    # 截图区顶/底发光线，标注"真机画面"边界
    sh = None
    if b.get("crop"):
        _, cx, cy, cw, ch = b["crop"]
        sh = round(W * ch / cw)
    if sh:
        for yy in (DEMO_Y - 2, DEMO_Y + sh + 1):
            d.line([0, yy, W, yy], fill=(64, 108, 172), width=3)

    cap = b.get("cap", [])
    if cap:
        f_cap = ImageFont.truetype(F_BOLD, 42)
        ch_ = 56
        cy0 = DEMO_Y + (sh or 600) + 70
        for i, line in enumerate(cap):
            wl = d.textbbox((0, 0), cn(line), font=f_cap)[2]
            while wl > W - 120 and f_cap.size > 24:
                f_cap = ImageFont.truetype(F_BOLD, f_cap.size - 2)
                wl = d.textbbox((0, 0), cn(line), font=f_cap)[2]
            fill = (150, 190, 240) if i == 0 else (226, 236, 250)
            d.text(((W - wl) // 2, cy0 + i * ch_), cn(line), font=f_cap, fill=fill)
    return im.convert("RGB")


def scene(b, idx, total, tag):
    if b.get("endcard"):
        return endcard(b)
    if b["kind"] in ("img", "video"):
        return demo_scene(b)
    im = bg()
    d = ImageDraw.Draw(im)
    px, py, pw, ph = PANEL

    # —— 标题条：左标题，右 EP 胶囊 ——
    f_title = ImageFont.truetype(F_BOLD, 48)
    title = cn(b.get("title", ""))
    while d.textbbox((0, 0), title, font=f_title)[2] > 800 and f_title.size > 28:
        f_title = ImageFont.truetype(F_BOLD, f_title.size - 2)
    d.text((84, TITLE_CY), title, font=f_title, fill=C_TITLE, anchor="lm")

    ep_label = ""
    if tag:
        parts = [p.strip() for p in tag.replace(" ", "").split("·")
                 if p.strip().upper().startswith("EP")]
        ep_label = parts[0] if parts else tag
    if ep_label:
        f_ep = ImageFont.truetype(F_BOLD, 28)
        ew = d.textbbox((0, 0), ep_label, font=f_ep)[2]
        pad = 26
        rx0, rx1 = EP_X - ew - pad, EP_X
        d.rounded_rectangle([rx0, TITLE_CY - 24, rx1, TITLE_CY + 24], radius=24, fill=C_ACCENT)
        d.text((rx1 - pad, TITLE_CY), ep_label, font=f_ep, fill=(255, 255, 255), anchor="rm")

    # —— 内容舞台：文字卡（媒体由 render 叠进同一区域）——
    if b["kind"] == "text":
        # 奶白框向上扩展吃满中段空白，并加一点透明度透出背景
        card = (56, 535, 1024, 1600)
        band = Image.open(WB_BG).convert("RGB").resize((W, H), Image.LANCZOS)
        band = band.crop((0, 540, W, 985)).resize((W, card[3] - card[1]), Image.LANCZOS)
        im.paste(band.filter(ImageFilter.GaussianBlur(26)), (0, card[1]))
        shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(shadow).rounded_rectangle(
            [card[0] + 4, card[1] + 14, card[2] - 4, card[3] + 12],
            radius=30, fill=(8, 16, 30, 110))
        im = Image.alpha_composite(im, shadow.filter(ImageFilter.GaussianBlur(20)))
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(layer).rounded_rectangle(card, radius=28, fill=CREAM + (196,))
        im = Image.alpha_composite(im, layer)
        d = ImageDraw.Draw(im)
        deco_icons(d, 660)
        lines = b.get("panel", [])
        n = len(lines)
        if n:
            size = 86 if n <= 2 else 60
            lh = 116 if n <= 2 else 86
            y0 = 1100 - lh * n // 2
            for i, line in enumerate(lines):
                fill = C_ACCENT if (i >= n - 1 and n >= 2) else C_TEXT
                f = ImageFont.truetype(F_BOLD, size)
                wl = d.textbbox((0, 0), cn(line), font=f)[2]
                while wl > pw - 40 and size > 24:
                    size -= 2
                    f = ImageFont.truetype(F_BOLD, size)
                    wl = d.textbbox((0, 0), cn(line), font=f)[2]
                d.text((px + (pw - wl) // 2, y0 + i * lh), cn(line), font=f, fill=fill)
            pass

    # —— 结论字幕（舞台底部，媒体压不到）——
    cap = b.get("cap", [])
    if cap:
        f_cap = ImageFont.truetype(F_BOLD, 34)
        lh = 42
        for i, line in enumerate(cap):
            wl = d.textbbox((0, 0), cn(line), font=f_cap)[2]
            while wl > pw - 40 and f_cap.size > 22:
                f_cap = ImageFont.truetype(F_BOLD, f_cap.size - 2)
                wl = d.textbbox((0, 0), cn(line), font=f_cap)[2]
            d.text((px + (pw - wl) // 2, CAP_Y0 + i * lh), cn(line), font=f_cap, fill=C_MUTED)

    return im.convert("RGB")


def fit_demo(src, x, y, w, h, out):
    """真机演示：截取区域按宽度铺满 1080，保持比例（整窗可见，不裁两侧）。"""
    im = Image.open(src).convert("RGB").crop((x, y, x + w, y + h))
    r = W / im.width
    im = im.resize((W, max(1, round(im.height * r))), Image.LANCZOS)
    im.save(out)
    return out


def sub_png(text, out, dark=False):
    """口播字幕：居中落进底部字幕条；真机页用深底白字。"""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    size = 42
    f = ImageFont.truetype(F_BOLD, size)
    wl = d.textbbox((0, 0), text, font=f)[2]
    if wl > 940:
        size = max(26, int(size * 940 / wl))
        f = ImageFont.truetype(F_BOLD, size)
        wl = d.textbbox((0, 0), text, font=f)[2]
    cx = W // 2
    if dark:
        bw, bh = wl + 90, 88
        d.rounded_rectangle([cx - bw // 2, SUB_CY - bh // 2, cx + bw // 2, SUB_CY + bh // 2],
                            radius=bh // 2, fill=(8, 12, 20, 190))
        d.text((cx + 2, SUB_CY + 2), text, font=f, fill=(0, 0, 0, 180), anchor="mm")
        d.text((cx, SUB_CY), text, font=f, fill=(255, 255, 255, 255), anchor="mm")
    else:
        d.text((cx + 2, SUB_CY + 2), text, font=f, fill=(255, 255, 255, 150), anchor="mm")
        d.text((cx, SUB_CY), text, font=f, fill=(28, 34, 50, 255), anchor="mm")
    im.save(out)
    return out


def split_lines(text, maxlen=24):
    parts = [p for p in re.findall(r"[^，。；：！？、]+[，。；：！？、]?", text) if p]
    out, cur = [], ""
    for p in parts:
        if len(cur) + len(p) <= maxlen:
            cur += p
        else:
            if cur:
                out.append(cur)
            while len(p) > maxlen:
                out.append(p[:maxlen])
                p = p[maxlen:]
            cur = p
    if cur:
        out.append(cur)
    return out


def make_subs(text, vdur, pre, name, dark=False):
    """按字数比例把旁白切成逐句字幕，铺满这句旁白的时长。"""
    lines = [cn(l) for l in split_lines(text)]
    lines = [l[:-1] if i < len(lines) - 1 and l and l[-1] in "，、；："
             else l for i, l in enumerate(lines)]
    total = sum(len(c) for c in lines) or 1
    subs, acc = [], 0
    for i, line in enumerate(lines):
        a = vdur * acc / total
        acc += len(line)
        b = vdur * acc / total
        png = sub_png(line, PARTS / f"{pre}-sub-{name}-{i}.png", dark=dark)
        subs.append((a, max(a + 0.35, b), png))
    return subs


def render(b, idx, total, dur, tag, pre, subs):
    bgp = PARTS / f"{pre}-bg-{b['name']}.png"
    scene(b, idx, total, tag).save(bgp)
    px, py, pw, ph = PANEL
    out = PARTS / f"{pre}-{b['name']}.mp4"
    enc = ["-t", f"{dur:.3f}", "-r", FPS, "-an", "-c:v", "libx264",
           "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p"]

    def mk_tail(base):
        t, label = "", "c"
        for i, (a, e, png) in enumerate(subs):
            t += (f"[{label}][{base + i}:v]overlay="
                  f"enable='between(t,{a:.3f},{e:.3f})'[s{i}];")
            label = f"s{i}"
        t += f"[{label}]format=yuv420p[o]"
        return t

    subin = [x for p in subs for x in ["-loop", "1", "-framerate", FPS, "-i", str(p[-1])]]

    if b["kind"] == "text":
        fc = "[0:v]null[c];" + mk_tail(1)
        run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-framerate", FPS, "-i", bgp]
            + subin + ["-filter_complex", fc, "-map", "[o]"] + enc + [out])
        return out

    if b["kind"] == "img" and "sec" in b:
        src = CHAT
        y0, y1 = b["sec"]
        sw, sh = Image.open(src).size
        win = int(round(sw * PANEL[3] / PANEL[2]))     # 铺满画面框的窗口高度
        win = min(win, sh)
        if y1 - y0 <= win:                              # 一段装得下：静止
            top = max(0, min(y0 - (win - (y1 - y0)) // 2, sh - win))
            head = (f"[0:v]crop={sw}:{win}:0:{top},scale={pw}:{ph},setsar=1[fg];"
                    f"[1:v][fg]overlay={px}:{py}:shortest=1[c];")
            first = "静止"
        else:
            top = max(0, min(y0, sh - win))
            bot = max(top, min(y1, sh) - win)
            hold, dy = 0.6, bot - top
            mv = max(0.3, dur - 1.2)
            ye = (f"if(lt(t,{hold:.2f}),{top},"
                  f"if(lt(t,{hold + mv:.2f}),{top}+{dy}*(t-{hold:.2f})/{mv:.2f},{bot}))")
            head = (f"[0:v]crop={sw}:{win}:0:'{ye}',scale={pw}:{ph},setsar=1[fg];"
                    f"[1:v][fg]overlay={px}:{py}:shortest=1[c];")
            first = f"滚动 {top}→{bot}"
        print(f"  {b['name']:5s} 截图 {first}  字幕 {len(subs)} 句")
        run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-framerate", FPS, "-i", src,
             "-loop", "1", "-framerate", FPS, "-i", bgp]
            + subin + ["-filter_complex", head + mk_tail(2), "-map", "[o]"] + enc + [out])
        return out

    if b["kind"] == "img":
        src, x, y, w, h = b["crop"]
        sl = fit_demo(src, x, y, w, h, SLI / f"{pre}-{b['name']}.png")
        head = f"[1:v][0:v]overlay=0:{DEMO_Y}:shortest=1[c];"
        run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-framerate", FPS, "-i", sl,
             "-loop", "1", "-framerate", FPS, "-i", bgp]
            + subin + ["-filter_complex", head + mk_tail(2), "-map", "[o]"] + enc + [out])
        return out

    mat = b["t_out"] - b["t_in"]
    speed = max(1.0, mat / dur)
    pad = max(0.4, dur - mat / speed + 1.0)
    if "vcrop" in b:
        cx, cy, cw, ch = b["vcrop"]
        head = (f"[0:v]crop={cw}:{ch}:{cx}:{cy},scale={W}:-2,setsar=1,fps={FPS},"
                f"setpts=(PTS-STARTPTS)/{speed:.4f},"
                f"tpad=stop_mode=clone:stop_duration={pad:.2f}[fg];"
                f"[1:v][fg]overlay=0:{DEMO_Y}:shortest=1[c];")
    else:
        head = (f"[0:v]scale={W}:-2,setsar=1,fps={FPS},setpts=(PTS-STARTPTS)/{speed:.4f},"
                f"tpad=stop_mode=clone:stop_duration={pad:.2f}[fg];"
                f"[1:v][fg]overlay=0:{DEMO_Y}:shortest=1[c];")
    run(["ffmpeg", "-y", "-v", "error", "-ss", f"{b['t_in']:.3f}", "-t", f"{mat:.3f}",
         "-i", b["src"], "-loop", "1", "-framerate", FPS, "-i", bgp]
        + subin + ["-filter_complex", head + mk_tail(2), "-map", "[o]"] + enc + [out])
    return out


def build_audio(acts, durs, pre):
    ins, fs, start = [], [], 0.0
    for i, (b, d) in enumerate(zip(acts, durs)):
        mp3 = tts(b["name"], b["voice"])
        ins += ["-i", str(mp3)]
        ms = int(start * 1000)
        fs.append(f"[{i}:a]adelay={ms}|{ms},apad[a{i}]")
        start += d
    total = start
    n = len(acts)
    fc = ";".join(fs) + ";" + "".join(f"[a{i}]" for i in range(n)) + \
        f"amix=inputs={n}:normalize=0:duration=longest,loudnorm=I=-16:TP=-1.5,aresample=48000[a]"
    out = PARTS / f"{pre}-audio.m4a"
    run(["ffmpeg", "-y", "-v", "error"] + ins +
        ["-filter_complex", fc, "-map", "[a]", "-t", f"{total:.3f}",
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", out])
    return out, total


def build(part, acts, tag):
    pre = f"ep{part}"
    final = OUT / f"{pre}.mp4"
    for p in (AUD, SLI, PARTS):
        p.mkdir(parents=True, exist_ok=True)
    durs, vdurs = [], []
    for b in acts:
        v = probe(tts(b["name"], b["voice"]))
        vdurs.append(v)
        durs.append(max(3.0, round((v + 0.55 + HOLD.get(b["name"], 0)) * FPS) / FPS))
    total = sum(durs)

    if "--preview" in sys.argv:
        for i, (b, d) in enumerate(zip(acts, durs)):
            scene(b, i, len(acts), tag).save(PARTS / f"{pre}-prev-{i:02d}-{b['name']}.png")
            print(f"{b['name']:6s} {d:6.2f}s")
        print(f"EP{part} 总长 {total:.2f}s")
        return

    print(f"EP{part}")
    for b in acts:
        if b["kind"] == "promo":
            p = make_promo(SLI / f"{pre}-promo.png")
            b["kind"] = "img"
            b["crop"] = (p, 0, 0, PANEL[2], PANEL[3])
    parts = [render(b, i, len(acts), d, tag, pre,
                    make_subs(b["voice"], v, pre, b["name"],
                              dark=b["kind"] in ("img", "video")))
             for i, (b, d, v) in enumerate(zip(acts, durs, vdurs))]
    lst = PARTS / f"{pre}-join.txt"
    lst.write_text("".join(f"file '{p.name}'\n" for p in parts), encoding="utf-8")
    v = PARTS / f"{pre}-video.mp4"
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst,
         "-c", "copy", v])
    a, dur = build_audio(acts, durs, pre)
    run(["ffmpeg", "-y", "-v", "error", "-i", v, "-i", a, "-c:v", "copy",
         "-c:a", "copy", "-movflags", "+faststart", "-t", f"{dur:.3f}", final])
    print(f"完成 {final}  {probe(final):.2f}s")



def load_beats(path):
    """beats.json -> acts；素材路径相对 json 所在目录。"""
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    base = path.parent
    acts = []
    for b in data["beats"]:
        b = dict(b)
        b.setdefault("kind", "video")
        if b.get("src"):
            p = Path(b["src"])
            b["src"] = p if p.is_absolute() else base / p
        if b.get("crop"):
            c = b["crop"]
            p = Path(c[0])
            b["crop"] = (p if p.is_absolute() else base / p, *[int(v) for v in c[1:]])
        if b.get("vcrop"):
            b["vcrop"] = tuple(int(v) for v in b["vcrop"])
        if b.get("avatar"):
            p = Path(b["avatar"])
            b["avatar"] = p if p.is_absolute() else base / p
        acts.append(b)
    return acts, data.get("tag", ""), str(data.get("ep", "01")), data.get("hold", {})


def main():
    args = sys.argv[1:]
    cfg = args[args.index("--beats") + 1] if "--beats" in args else "beats.json"
    acts, tag, ep, hold = load_beats(cfg)
    HOLD.update(hold)
    build(ep, acts, tag)


if __name__ == "__main__":
    main()
