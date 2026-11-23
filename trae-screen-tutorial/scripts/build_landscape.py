# -*- coding: utf-8 -*-
"""横版 16:9（1920x1080）同物料出片，复用 beats.json 与已缓存配音。

    python tools/build_landscape.py --beats episodes/EP01/beats.json
    python tools/build_landscape.py --beats episodes/EP01/beats.json --preview

真机页截图近 16:9，直接满屏；PPT 页做成宽幅半透明奶油卡。
"""
import asyncio
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import edge_tts
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = Path.cwd() / "build"
AUD = OUT / "audio"
PARTS = OUT / "parts16"
SLI = OUT / "slides16"

W, H, FPS = 1920, 1080, 30
VOICE, RATE = "zh-CN-YunxiNeural", "+8%"

# 品牌头像随技能打包，即插即用；可用环境变量 WB_AVATAR 覆盖
SKILL_DIR = Path(__file__).resolve().parent.parent
WB_AVATAR = Path(os.environ.get("WB_AVATAR", str(SKILL_DIR / "assets" / "avatar.jpg")))

CREAM = (251, 245, 230)
C_TEXT = (28, 34, 50)
C_ACCENT = (48, 110, 190)
C_MUTED = (90, 110, 140)
SUB_CY = 1000

F_BOLD = r"C:\Windows\Fonts\msyhbd.ttc"
F_REG = r"C:\Windows\Fonts\msyh.ttc"


def cn(text):
    cjk = r"[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]"
    text = re.sub(rf"(?<={cjk}) +", "", text)
    text = re.sub(rf" +(?={cjk})", "", text)
    return text


def run(cmd):
    subprocess.run([str(c) for c in cmd], check=True)


def probe(p):
    o = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(p)], capture_output=True, text=True)
    return float(o.stdout.strip())


def tts(name, text):
    key = hashlib.sha1((VOICE + RATE + text).encode()).hexdigest()[:10]
    out = AUD / f"{name}_{key}.mp3"
    if not out.exists():
        tmp = out.with_suffix(".part")
        asyncio.run(edge_tts.Communicate(text, VOICE, rate=RATE).save(str(tmp)))
        tmp.rename(out)
    return out


def grad_bg():
    top, bot = (16, 24, 38), (6, 9, 14)
    im = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(im)
    for y in range(H):
        t = y / (H - 1)
        d.line([(0, y), (W, y)], fill=tuple(int(top[k] + (bot[k] - top[k]) * t) for k in range(3)))
    return im


def cover(im):
    r = max(W / im.width, H / im.height)
    im = im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)
    l, t = (im.width - W) // 2, (im.height - H) // 2
    return im.crop((l, t, l + W, t + H))


def paste_avatar(im, cx, cy, dia):
    av = Image.open(WB_AVATAR).convert("RGBA").resize((dia, dia), Image.LANCZOS)
    mask = Image.new("L", (dia, dia), 0)
    ImageDraw.Draw(mask).ellipse([6, 6, dia - 6, dia - 6], fill=255)
    ImageDraw.Draw(im).ellipse([cx - dia // 2 - 8, cy - dia // 2 - 8,
                                cx + dia // 2 + 8, cy + dia // 2 + 8],
                               outline=(255, 255, 255, 220), width=4)
    im.paste(av, (cx - dia // 2, cy - dia // 2), mask)


def pill(d, text, x, y, size=48, pad=32, fill=C_ACCENT):
    t = cn(text)
    f = ImageFont.truetype(F_BOLD, size)
    while d.textbbox((0, 0), t, font=f)[2] > 1200 and size > 28:
        size -= 2
        f = ImageFont.truetype(F_BOLD, size)
    tw = d.textbbox((0, 0), t, font=f)[2]
    h = size + 30
    d.rounded_rectangle([x, y, x + tw + pad * 2, y + h], radius=h // 2, fill=fill)
    d.text((x + pad, y + h // 2), t, font=f, fill=(255, 255, 255), anchor="lm")


def scene_text(b):
    im = grad_bg().convert("RGBA")
    paste_avatar(im, 172, 172, 196)
    d = ImageDraw.Draw(im)
    pill(d, b.get("title", ""), 330, 130, 48)

    card = (90, 330, 1830, 860)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(layer).rounded_rectangle(card, radius=32, fill=CREAM + (238,))
    im = Image.alpha_composite(im, layer)
    d = ImageDraw.Draw(im)

    lines = b.get("panel", [])
    n = len(lines)
    if n:
        size = 104 if n <= 2 else 74
        lh = 140 if n <= 2 else 100
        y0 = card[1] + (card[3] - card[1] - lh * n) // 2 - 30
        for i, line in enumerate(lines):
            fill = C_ACCENT if (i >= n - 1 and n >= 2) else C_TEXT
            f = ImageFont.truetype(F_BOLD, size)
            wl = d.textbbox((0, 0), cn(line), font=f)[2]
            while wl > 1660 and size > 40:
                size -= 2
                f = ImageFont.truetype(F_BOLD, size)
                wl = d.textbbox((0, 0), cn(line), font=f)[2]
            d.text(((W - wl) // 2, y0 + i * lh), cn(line), font=f, fill=fill)
    cap = b.get("cap", [])
    if cap:
        f = ImageFont.truetype(F_REG, 38)
        yy = card[3] - 120
        for i, line in enumerate(cap):
            wl = d.textbbox((0, 0), cn(line), font=f)[2]
            d.text(((W - wl) // 2, yy + i * 50), cn(line), font=f, fill=C_MUTED)
    return im.convert("RGB")


def scene_demo(b, out):
    src, x, y, w, h = b["crop"]
    im = cover(Image.open(src).convert("RGB").crop((x, y, x + w, y + h)))
    d = ImageDraw.Draw(im)
    pill(d, b.get("title", ""), 64, 64, 46)
    im.save(out)
    return out


def scene_end(b):
    im = Image.new("RGB", (W, H), (243, 246, 250)).convert("RGBA")
    paste_avatar(im, 560, 540, 420)
    d = ImageDraw.Draw(im)
    lines = b.get("panel", [])
    x = 900
    if len(lines) >= 1:
        f = ImageFont.truetype(F_BOLD, 44)
        d.text((x, 400), cn(lines[0]), font=f, fill=C_MUTED)
    if len(lines) >= 2:
        f = ImageFont.truetype(F_BOLD, 120)
        d.text((x, 470), cn(lines[1]), font=f, fill=C_ACCENT)
    if len(lines) >= 3:
        f = ImageFont.truetype(F_REG, 42)
        d.text((x, 660), cn(lines[2]), font=f, fill=C_MUTED)
    return im.convert("RGB")


def sub_png(text, out, dark_text=False):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    size = 48
    f = ImageFont.truetype(F_BOLD, size)
    wl = d.textbbox((0, 0), text, font=f)[2]
    if wl > 1560:
        size = max(32, int(size * 1560 / wl))
        f = ImageFont.truetype(F_BOLD, size)
        wl = d.textbbox((0, 0), text, font=f)[2]
    cx = W // 2
    if dark_text:
        d.text((cx + 2, SUB_CY + 2), text, font=f, fill=(255, 255, 255, 150), anchor="mm")
        d.text((cx, SUB_CY), text, font=f, fill=(28, 34, 50), anchor="mm")
    else:
        bw, bh = wl + 110, 100
        d.rounded_rectangle([cx - bw // 2, SUB_CY - bh // 2, cx + bw // 2, SUB_CY + bh // 2],
                            radius=bh // 2, fill=(8, 12, 20, 180))
        d.text((cx + 2, SUB_CY + 2), text, font=f, fill=(0, 0, 0, 170), anchor="mm")
        d.text((cx, SUB_CY), text, font=f, fill=(255, 255, 255), anchor="mm")
    im.save(out)
    return out


def split_lines(text, maxlen=26):
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
    lines = [cn(l) for l in split_lines(text)]
    lines = [l[:-1] if i < len(lines) - 1 and l and l[-1] in "，、；：" else l
             for i, l in enumerate(lines)]
    total = sum(len(c) for c in lines) or 1
    subs, acc = [], 0
    for i, line in enumerate(lines):
        a = vdur * acc / total
        acc += len(line)
        b = vdur * acc / total
        png = sub_png(line, PARTS / f"{pre}-sub-{name}-{i}.png", dark_text=dark)
        subs.append((a, max(a + 0.35, b), png))
    return subs


def title_overlay(b, out):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pill(ImageDraw.Draw(im), b.get("title", ""), 64, 64, 46)
    im.save(out)
    return out


def render_video_seg(b, dur, pre, subs):
    tp = title_overlay(b, PARTS / f"{pre}-title-{b['name']}.png")
    t_in, t_out = b.get("t_in", 0), b["t_out"]
    pad = max(0.2, dur - (t_out - t_in))
    out = PARTS / f"{pre}-{b['name']}.mp4"
    enc = ["-t", f"{dur:.3f}", "-r", FPS, "-an", "-c:v", "libx264",
           "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p"]
    head = (f"[0:v]trim={t_in:.3f}:{t_out:.3f},setpts=PTS-STARTPTS,"
            f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
            f"fps={FPS},tpad=stop_mode=clone:stop_duration={pad:.2f}[v0];"
            f"[v0][1:v]overlay[c];")
    t, label = "", "c"
    for i, (a, e, png) in enumerate(subs):
        t += f"[{label}][{2 + i}:v]overlay=enable='between(t,{a:.3f},{e:.3f})'[s{i}];"
        label = f"s{i}"
    t += f"[{label}]format=yuv420p[o]"
    subin = [x for p in subs for x in ["-loop", "1", "-framerate", FPS, "-i", str(p[-1])]]
    run(["ffmpeg", "-y", "-v", "error", "-i", str(b["src"]),
         "-loop", "1", "-framerate", FPS, "-i", tp]
        + subin + ["-filter_complex", head + t, "-map", "[o]"] + enc + [out])
    return out


def render_seg(b, dur, pre, subs):
    if b["kind"] == "video":
        return render_video_seg(b, dur, pre, subs)
    base = PARTS / f"{pre}-base-{b['name']}.png"
    if b.get("endcard"):
        scene_end(b).save(base)
    elif b["kind"] == "img":
        scene_demo(b, base)
    else:
        scene_text(b).save(base)
    out = PARTS / f"{pre}-{b['name']}.mp4"
    enc = ["-t", f"{dur:.3f}", "-r", FPS, "-an", "-c:v", "libx264",
           "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p"]
    t, label = "", "c"
    for i, (a, e, png) in enumerate(subs):
        t += f"[{label}][{1 + i}:v]overlay=enable='between(t,{a:.3f},{e:.3f})'[s{i}];"
        label = f"s{i}"
    t += f"[{label}]format=yuv420p[o]"
    subin = [x for p in subs for x in ["-loop", "1", "-framerate", FPS, "-i", str(p[-1])]]
    run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-framerate", FPS, "-i", base]
        + subin + ["-filter_complex", "[0:v]null[c];" + t, "-map", "[o]"] + enc + [out])
    return out


def build_audio(acts, durs, pre):
    ins, start = [], 0.0
    for b, d in zip(acts, durs):
        ins += ["-i", str(tts(b["name"], b["voice"]))]
        start += d
    fs, s = [], 0.0
    for i, (b, d) in enumerate(zip(acts, durs)):
        ms = int(s * 1000)
        fs.append(f"[{i}:a]adelay={ms}|{ms},apad[a{i}]")
        s += d
    n = len(acts)
    fc = ";".join(fs) + ";" + "".join(f"[a{i}]" for i in range(n)) + \
        f"amix=inputs={n}:normalize=0:duration=longest,loudnorm=I=-16:TP=-1.5,aresample=48000[a]"
    out = PARTS / f"{pre}-audio.m4a"
    run(["ffmpeg", "-y", "-v", "error"] + ins + ["-filter_complex", fc, "-map", "[a]",
         "-t", f"{start:.3f}", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", out])
    return out, start


def main():
    args = sys.argv[1:]
    cfg = args[args.index("--beats") + 1] if "--beats" in args else "beats.json"
    path = Path(cfg)
    data = json.loads(path.read_text(encoding="utf-8"))
    base = path.parent
    hold = data.get("hold", {})
    acts = []
    for b in data["beats"]:
        b = dict(b)
        b.setdefault("kind", "video")
        if b.get("crop"):
            c = b["crop"]
            p = Path(c[0])
            b["crop"] = (p if p.is_absolute() else base / p, *[int(v) for v in c[1:]])
        if b.get("src"):
            p = Path(b["src"])
            b["src"] = p if p.is_absolute() else base / p
        acts.append(b)
    ep = str(data.get("ep", "01"))
    pre = f"L{ep}"
    for d in (AUD, PARTS, SLI):
        d.mkdir(parents=True, exist_ok=True)

    durs, vdurs = [], []
    for b in acts:
        v = probe(tts(b["name"], b["voice"]))
        vdurs.append(v)
        durs.append(max(3.0, round((v + 0.55 + hold.get(b["name"], 0)) * FPS) / FPS))

    if "--preview" in args:
        for i, (b, d) in enumerate(zip(acts, durs)):
            if b.get("endcard"):
                scene_end(b).save(PARTS / f"{pre}-prev-{i:02d}-{b['name']}.png")
            elif b["kind"] == "video":
                fr = PARTS / f"{pre}-prev-{i:02d}-{b['name']}.png"
                run(["ffmpeg", "-y", "-v", "error", "-ss", f"{b.get('t_in', 0) + 0.1:.3f}",
                     "-i", b["src"], "-frames:v", "1",
                     "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}",
                     fr])
                Image.open(fr).save(fr)
            elif b["kind"] == "img":
                scene_demo(b, PARTS / f"{pre}-prev-{i:02d}-{b['name']}.png")
            else:
                scene_text(b).save(PARTS / f"{pre}-prev-{i:02d}-{b['name']}.png")
            print(f"{b['name']:6s} {d:6.2f}s")
        print(f"EP{ep} 横版总长 {sum(durs):.2f}s")
        return

    print(f"EP{ep} 横版")
    segs = [render_seg(b, d, pre, make_subs(b["voice"], v, pre, b["name"],
                                            dark=b.get("endcard", False)))
            for b, d, v in zip(acts, durs, vdurs)]
    lst = PARTS / f"{pre}-join.txt"
    lst.write_text("".join(f"file '{p.name}'\n" for p in segs), encoding="utf-8")
    vv = PARTS / f"{pre}-video.mp4"
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", vv])
    a, dur = build_audio(acts, durs, pre)
    final = OUT / f"ep{ep}-16x9.mp4"
    run(["ffmpeg", "-y", "-v", "error", "-i", vv, "-i", a, "-c:v", "copy", "-c:a", "copy",
         "-movflags", "+faststart", "-t", f"{dur:.3f}", final])
    print(f"完成 {final}  {probe(final):.2f}s")


if __name__ == "__main__":
    main()
