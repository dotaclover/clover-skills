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
VOICE, RATE = "zh-TW-YunJheNeural", "+18%"

SERIES = "顺哥 TRAE 教程系列"

PANEL = (60, 316, 960, 1200)
CAP_TOP, DOT_Y = 1580, 1534

C_TOP, C_BOT = (8, 11, 16), (15, 21, 29)
C_ACCENT = (18, 227, 155)
C_TEXT = (243, 246, 250)
C_DIM = (138, 152, 168)
C_LINE = (28, 37, 49)
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


def bg():
    im = Image.new("RGB", (W, H), C_TOP)
    d = ImageDraw.Draw(im)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)],
               fill=tuple(int(C_TOP[i] + (C_BOT[i] - C_TOP[i]) * t) for i in range(3)))
    return im


def scene(b, idx, total, tag):
    im = bg().convert("RGBA")
    px, py, pw, ph = PANEL
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([px - 6, py - 4, px + pw + 6, py + ph + 16],
                                         radius=20, fill=(0, 0, 0, 145))
    im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(18)))
    d = ImageDraw.Draw(im)

    f_series = ImageFont.truetype(F_REG, 28)
    d.ellipse([70, 68, 82, 80], fill=C_ACCENT)
    d.text((98, 58), SERIES, font=f_series, fill=C_DIM)
    tw = d.textbbox((0, 0), tag, font=f_series)[2]
    d.text((W - 70 - tw, 58), tag, font=f_series, fill=C_DIM)

    if b["step"]:
        f_step = ImageFont.truetype(F_BOLD, 60)
        f_ch = ImageFont.truetype(F_BOLD, 36)
        d.text((70, 116), b["step"], font=f_step, fill=C_ACCENT)
        sw = d.textbbox((0, 0), b["step"], font=f_step)[2]
        d.text((70 + sw + 16, 138), cn(b["chapter"]), font=f_ch, fill=C_TEXT)
        f_title = ImageFont.truetype(F_BOLD, 58)
        d.text((70, 200), cn(b["title"]), font=f_title, fill=C_TEXT)
    d.line([(70, 312), (W - 70, 312)], fill=C_LINE, width=2)

    d.rounded_rectangle([px, py, px + pw, py + ph], radius=8, fill=(0, 0, 0),
                        outline=C_BORDER, width=2)

    if b["kind"] == "text":
        d.rounded_rectangle([px, py, px + 8, py + ph], radius=4, fill=C_ACCENT)
        y0 = py + (ph - 140 * len(b["panel"])) // 2
        for i, line in enumerate(b["panel"]):
            size = 46 if i >= 2 else 80
            f = ImageFont.truetype(F_BOLD, size)
            wl = d.textbbox((0, 0), line, font=f)[2]
            while wl > pw - 70 and size > 22:      # 地址这种长行自动缩
                size -= 2
                f = ImageFont.truetype(F_BOLD, size)
                wl = d.textbbox((0, 0), line, font=f)[2]
            d.text((px + (pw - wl) // 2, y0 + i * 140), line, font=f,
                   fill=C_TEXT if i < 2 else C_ACCENT)

    f_cap = ImageFont.truetype(F_BOLD, 56)
    for i, line in enumerate(b["cap"]):
        d.text((70, CAP_TOP + i * 84), cn(line), font=f_cap,
               fill=C_TEXT if i == 0 else C_DIM)

    x = 70
    for i in range(total):
        d.ellipse([x, DOT_Y, x + 13, DOT_Y + 13],
                  fill=C_ACCENT if i == idx else (56, 70, 88))
        x += 25
    return im.convert("RGB")


def fit_png(src, x, y, w, h, out):
    im = Image.open(src).convert("RGB").crop((x, y, x + w, y + h))
    pw, ph = PANEL[2], PANEL[3]
    r = min(pw / im.width, ph / im.height)
    im = im.resize((int(im.width * r), int(im.height * r)), Image.LANCZOS)
    canvas = Image.new("RGB", (pw, ph), (0, 0, 0))
    canvas.paste(im, ((pw - im.width) // 2, (ph - im.height) // 2))
    canvas.save(out)
    return out


def sub_png(text, out):
    """口播字幕：底部空白区一行，超宽自动缩字号。"""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    size = 40
    f = ImageFont.truetype(F_BOLD, size)
    wl = d.textbbox((0, 0), text, font=f)[2]
    if wl > 980:
        size = max(26, int(size * 980 / wl))
        f = ImageFont.truetype(F_BOLD, size)
        wl = d.textbbox((0, 0), text, font=f)[2]
    d.text(((W - wl) // 2, 1778), text, font=f, fill=(255, 255, 255, 246),
           stroke_width=3, stroke_fill=(0, 0, 0, 200))
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


def make_subs(text, vdur, pre, name):
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
        png = sub_png(line, PARTS / f"{pre}-sub-{name}-{i}.png")
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
        t += (f"[{label}]drawbox=x={px}:y={py}:w={pw}:h={ph}:"
              f"color=0x2E3C4E@0.9:t=2,format=yuv420p[o]")
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
        sl = fit_png(src, x, y, w, h, SLI / f"{pre}-{b['name']}.png")
        head = (f"[0:v]scale={pw}:{ph},setsar=1[fg];"
                f"[1:v][fg]overlay={px}:{py}:shortest=1[c];")
        run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-framerate", FPS, "-i", sl,
             "-loop", "1", "-framerate", FPS, "-i", bgp]
            + subin + ["-filter_complex", head + mk_tail(2), "-map", "[o]"] + enc + [out])
        return out

    mat = b["t_out"] - b["t_in"]
    speed = max(1.0, mat / dur)
    pad = max(0.4, dur - mat / speed + 1.0)
    if "vcrop" in b:
        cx, cy, cw, ch = b["vcrop"]
        head = (f"[0:v]crop={cw}:{ch}:{cx}:{cy},scale={pw}:{ph},setsar=1,fps={FPS},"
                f"setpts=(PTS-STARTPTS)/{speed:.4f},"
                f"tpad=stop_mode=clone:stop_duration={pad:.2f}[fg];"
                f"[1:v][fg]overlay={px}:{py}:shortest=1[c];")
    else:
        head = (f"[0:v]scale={pw}:{ph}:force_original_aspect_ratio=decrease,"
                f"pad={pw}:{ph}:(ow-iw)/2:(oh-ih)/2:color=black,"
                f"setsar=1,fps={FPS},setpts=(PTS-STARTPTS)/{speed:.4f},"
                f"tpad=stop_mode=clone:stop_duration={pad:.2f}[fg];"
                f"[1:v][fg]overlay={px}:{py}:shortest=1[c];")
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
                    make_subs(b["voice"], v, pre, b["name"]))
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
