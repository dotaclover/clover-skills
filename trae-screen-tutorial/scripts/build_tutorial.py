# -*- coding: utf-8 -*-
"""录屏 → 9:16 教程短片合成器。

唯一的输入是 beats.json：
  - 每拍指定录屏文件、时间窗、原分辨率裁切框、步骤号/标题/字幕/配音词
  - 片头片尾可选
  - 自动生成背景卡、模糊铺底、逐拍变速、配音混音、拼接与验收

用法：
    python build_tutorial.py --config beats.json --preview    # 只出每拍静帧
    python build_tutorial.py --config beats.json              # 全量出片
"""
import argparse
import asyncio
import hashlib
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
U = H / 1920.0

PANEL = (60, 326, 960, 980)
CAPTION_TOP = 1396
DOT_Y = 1342

DEFAULTS = {
    "brand": "AI 从零开始",
    "episode": "Part01",
    "fonts": {"bold": r"C:\Windows\Fonts\msyhbd.ttc", "regular": r"C:\Windows\Fonts\msyh.ttc"},
    "theme": {
        "bg_top": "#090D12", "bg_bottom": "#111821", "accent": "#12E39B",
        "text": "#F2F6FA", "dim": "#8B9AAB", "line": "#1E2836", "border": "#2E3C4E",
    },
    "voice": {"enabled": True, "name": "zh-CN-XiaoxiaoNeural", "rate": "+8%"},
    "min_dur": 4.3,
    "out_name": "tutorial",
}


def hexc(s):
    s = s.lstrip("#")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def run(cmd):
    import subprocess
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-1800:])
        raise SystemExit(1)
    return r


def probe(path):
    import subprocess
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        raise SystemExit(f"ffprobe 读不出时长：{path}")
    return float(r.stdout.strip())


def frame_size(path):
    import subprocess
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                        "-show_entries", "stream=width,height", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"ffprobe 读不出尺寸：{path}")
    w, h = r.stdout.strip().split(",")[:2]
    return int(w), int(h)


class Ctx:
    def __init__(self, cfg, root):
        self.cfg = cfg
        self.root = root
        self.build = root / "_build"
        self.audio = root / "audio"
        self.out = root / "成片"
        t = cfg["theme"]
        self.C_TOP = hexc(t["bg_top"])
        self.C_BOT = hexc(t["bg_bottom"])
        self.C_ACCENT = hexc(t["accent"])
        self.C_TEXT = hexc(t["text"])
        self.C_DIM = hexc(t["dim"])
        self.C_LINE = hexc(t["line"])
        self.C_BORDER = hexc(t["border"])
        self.f_bold = cfg["fonts"]["bold"]
        self.f_reg = cfg["fonts"]["regular"]
        for p in (self.f_bold, self.f_reg):
            if not Path(p).exists():
                raise SystemExit(f"字体不存在：{p}（在 beats.json 的 fonts 里改成你机器上的字体）")
        self._bg = None

    def font(self, bold, size):
        return ImageFont.truetype(self.f_bold if bold else self.f_reg, size)

    def bg(self):
        if self._bg is None:
            im = Image.new("RGB", (W, H), self.C_TOP)
            d = ImageDraw.Draw(im)
            for y in range(H):
                k = y / (H - 1)
                d.line([(0, y), (W, y)], fill=tuple(
                    int(self.C_TOP[i] + (self.C_BOT[i] - self.C_TOP[i]) * k) for i in range(3)))
            ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            od = ImageDraw.Draw(ov)
            for y in range(0, H, 48):
                for x in range(0, W, 48):
                    od.ellipse([x, y, x + 2, y + 2], fill=(120, 160, 190, 16))
            self._bg = Image.alpha_composite(im.convert("RGBA"), ov).convert("RGB")
        return self._bg.copy()


# ------------------------------ 配音 ------------------------------

def voice_file(ctx, text, tag):
    if not ctx.cfg["voice"]["enabled"]:
        return None
    key = hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]
    out = ctx.audio / f"{tag}-{key}.mp3"
    if out.exists() and out.stat().st_size > 1000:
        return out
    try:
        import edge_tts
    except ImportError:
        raise SystemExit("开了配音但没装 edge-tts：pip install edge-tts，或把 voice.enabled 设为 false")
    asyncio.run(edge_tts.Communicate(text, ctx.cfg["voice"]["name"],
                                     rate=ctx.cfg["voice"]["rate"]).save(str(out)))
    return out


def vlen(ctx, text, tag):
    p = voice_file(ctx, text, tag)
    return probe(p) if p else 0.0


# ------------------------------ 背景卡 ------------------------------

def header(ctx, d, step, title):
    f_brand = ctx.font(False, 30)
    f_num = ctx.font(True, 112)
    f_title = ctx.font(True, 58)
    d.ellipse([60, 68, 74, 82], fill=ctx.C_ACCENT)
    d.text((90, 58), ctx.cfg["brand"], font=f_brand, fill=ctx.C_DIM)
    ep = ctx.cfg["episode"]
    nb = d.textbbox((0, 0), ep, font=f_brand)
    d.text((W - 60 - (nb[2] - nb[0]), 58), ep, font=f_brand, fill=ctx.C_DIM)
    d.text((58, 108), step, font=f_num, fill=ctx.C_ACCENT)
    nw = d.textbbox((0, 0), step, font=f_num)[2] - d.textbbox((0, 0), step, font=f_num)[0]
    d.text((58 + nw + 26, 148), title, font=f_title, fill=ctx.C_TEXT)
    d.line([(60, 292), (W - 60, 292)], fill=ctx.C_LINE, width=2)


def caption(ctx, d, lines):
    f = ctx.font(True, 54)
    lh = 78
    block = lh * len(lines)
    d.rounded_rectangle([60, CAPTION_TOP, 68, CAPTION_TOP + block - 12], radius=4, fill=ctx.C_ACCENT)
    for i, line in enumerate(lines):
        d.text((92, CAPTION_TOP + i * lh), line, font=f,
               fill=ctx.C_TEXT if i == 0 else ctx.C_DIM)


def dots(ctx, d, idx, total):
    x = 60
    for i in range(total):
        c = ctx.C_ACCENT if i == idx else (58, 72, 90)
        d.ellipse([x, DOT_Y, x + 14, DOT_Y + 14], fill=c)
        x += 26


def panel_shadow(ctx):
    px, py, pw, ph = PANEL
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sh)
    sd.rounded_rectangle([px - 10, py - 6, px + pw + 10, py + ph + 22], radius=26, fill=(0, 0, 0, 150))
    return sh.filter(ImageFilter.GaussianBlur(18))


def beat_bg(ctx, b, idx, total):
    im = Image.alpha_composite(ctx.bg().convert("RGBA"), panel_shadow(ctx))
    d = ImageDraw.Draw(im)
    header(ctx, d, b["step"], b["title"])
    caption(ctx, d, b["cap"])
    dots(ctx, d, idx, total)
    return im.convert("RGB")


def card_intro(ctx, cfg):
    im = ctx.bg()
    d = ImageDraw.Draw(im)
    d.text((72, 120), cfg.get("kicker", ""), font=ctx.font(True, 34), fill=ctx.C_ACCENT)
    f_big = ctx.font(True, 92)
    f_sub = ctx.font(False, 40)
    y = 540
    for i, line in enumerate(cfg["lines"]):
        d.text((72, y + i * 124), line, font=f_big,
               fill=ctx.C_TEXT if i < len(cfg["lines"]) - 1 else ctx.C_ACCENT)
    n = len(cfg["lines"])
    d.line([(76, y + n * 124 + 44), (500, y + n * 124 + 44)], fill=ctx.C_ACCENT, width=6)
    d.text((76, y + n * 124 + 84), cfg.get("sub", ""), font=f_sub, fill=ctx.C_DIM)
    return im


def card_outro(ctx, cfg):
    im = ctx.bg()
    d = ImageDraw.Draw(im)
    f_big = ctx.font(True, 96)
    f_name = ctx.font(True, 46)
    f_desc = ctx.font(False, 32)
    lines = cfg["title"]
    for i, line in enumerate(lines):
        d.text((72, 250 + i * 116), line, font=f_big,
               fill=ctx.C_TEXT if i == 0 else ctx.C_ACCENT)
    y = 680
    for name, desc in cfg["cards"]:
        d.rounded_rectangle([60, y, W - 60, y + 200], radius=18, fill=(15, 21, 29),
                            outline=ctx.C_BORDER, width=2)
        d.rounded_rectangle([60, y, 70, y + 200], radius=4, fill=ctx.C_ACCENT)
        d.text((100, y + 34), name, font=f_name, fill=ctx.C_TEXT)
        d.text((100, y + 104), desc, font=f_desc, fill=ctx.C_DIM)
        y += 236
    d.text((72, H - 170), cfg.get("footer", ""), font=ctx.font(False, 32), fill=ctx.C_DIM)
    return im


# ------------------------------ 规划 / 渲染 ------------------------------

def fit(crop):
    cw, ch = crop[0], crop[1]
    s = min((PANEL[2] - 8) / cw, (PANEL[3] - 8) / ch)
    tw, th = int(cw * s) // 2 * 2, int(ch * s) // 2 * 2
    return tw, th, PANEL[0] + (PANEL[2] - tw) // 2, PANEL[1] + (PANEL[3] - th) // 2


def check_beats(ctx, beats):
    for b in beats:
        src = Path(b["src"])
        if not src.exists():
            raise SystemExit(f"{b['name']}: 找不到素材 {src}")
        fw, fh = frame_size(src)
        cw, ch, cx, cy = b["crop"]
        if cx + cw > fw or cy + ch > fh or min(cw, ch, cx, cy) < 0:
            raise SystemExit(f"{b['name']}: crop 越界 {b['crop']}，素材是 {fw}x{fh}")
        if not (0 <= b["t_in"] < b["t_out"] <= probe(src) + 0.05):
            raise SystemExit(f"{b['name']}: 时间窗 {b['t_in']}-{b['t_out']} 超出素材时长")
        for line in b["cap"]:
            if len(line) > 17:
                print(f"  ! {b['name']} 字幕偏长（{len(line)} 字）：{line}")


def plan(ctx, beats):
    md = ctx.cfg["min_dur"]
    out = []
    for b in beats:
        if ctx.cfg["voice"]["enabled"]:
            dur = max(md, vlen(ctx, b["voice"], b["name"]) + 0.55)
        else:
            dur = max(md, float(b.get("dur", md)))
        out.append(dict(b, dur=round(dur, 2)))
    return out


def render_beat(ctx, b, bg_path):
    tw, th, px, py = fit(b["crop"])
    mat = b["t_out"] - b["t_in"]
    speed = max(1.0, min(mat / b["dur"], ctx.cfg.get("max_speed", 2.6)))
    cw, ch, cx, cy = b["crop"]
    px0, py0, pw0, ph0 = PANEL
    fc = (
        f"[1:v]crop={cw}:{ch}:{cx}:{cy},split=2[c1][c2];"
        f"[c1]scale={pw0}:{ph0}:force_original_aspect_ratio=increase,crop={pw0}:{ph0},"
        f"boxblur=30:3,lutrgb=r=val*0.26:g=val*0.28:b=val*0.34,setsar=1,fps={FPS}[fill];"
        f"[c2]scale={tw}:{th}:flags=lanczos,setsar=1,fps={FPS},"
        f"setpts=(PTS-STARTPTS)/{speed:.4f},tpad=stop_mode=clone:stop_duration=4[fg];"
        f"[0:v][fill]overlay={px0}:{py0}[b];"
        f"[b][fg]overlay={px}:{py}:shortest=1,"
        f"drawbox=x={px0}:y={py0}:w={pw0}:h={ph0}:color={ctx.cfg['theme']['border']}@0.95:t=2,"
        f"format=yuv420p[o]"
    )
    out = ctx.build / f"{b['name']}.mp4"
    run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-framerate", str(FPS), "-i", bg_path,
         "-ss", f"{b['t_in']:.3f}", "-t", f"{mat:.3f}", "-i", b["src"],
         "-filter_complex", fc, "-map", "[o]", "-t", f"{b['dur']:.3f}", "-r", str(FPS),
         "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", out])
    return out, speed


def render_card(ctx, im, dur, tag):
    png = ctx.build / f"{tag}.png"
    im.save(png)
    out = ctx.build / f"{tag}.mp4"
    run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-framerate", str(FPS), "-i", png,
         "-t", f"{dur:.3f}", "-r", str(FPS), "-an", "-c:v", "libx264", "-preset", "medium",
         "-crf", "16", "-pix_fmt", "yuv420p", out])
    return out


def mix_audio(ctx, events, total):
    """events: [(start_sec, mp3_path)]"""
    if not events:
        return None
    inputs = ["-f", "lavfi", "-t", f"{total:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
    for _, p in events:
        inputs += ["-i", p]
    fc = []
    for i, (t0, _) in enumerate(events, start=1):
        ms = int(round(t0 * 1000))
        fc.append(f"[{i}:a]aformat=sample_fmts=fltp:channel_layouts=stereo,aresample=48000,"
                  f"adelay={ms}|{ms}[a{i}]")
    fc.append("[0:a]" + "".join(f"[a{i}]" for i in range(1, len(events) + 1)) +
              f"amix=inputs={len(events) + 1}:normalize=0:dropout_transition=0,"
              f"alimiter=limit=0.95,atrim=0:{total:.3f}[out]")
    out = ctx.build / "voice.m4a"
    run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", ";".join(fc),
         "-map", "[out]", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", out])
    return out


def preview(ctx, intro, beats, outro):
    pdir = ctx.build / "preview"
    pdir.mkdir(parents=True, exist_ok=True)
    if intro:
        card_intro(ctx, intro).save(pdir / "00-intro.jpg", quality=88)
    for i, b in enumerate(beats):
        bg = pdir / f"bg-{b['name']}.png"
        beat_bg(ctx, b, i, len(beats)).save(bg)
        tw, th, px, py = fit(b["crop"])
        cw, ch, cx, cy = b["crop"]
        mid = (b["t_in"] + b["t_out"]) / 2
        tmp = pdir / f"crop-{b['name']}.png"
        run(["ffmpeg", "-y", "-v", "error", "-ss", f"{mid:.3f}", "-i", b["src"],
             "-frames:v", "1", "-vf", f"crop={cw}:{ch}:{cx}:{cy},scale={tw}:{th}:flags=lanczos",
             tmp])
        im = Image.open(bg).convert("RGB")
        sub = Image.open(tmp).convert("RGB")
        pw, ph = PANEL[2], PANEL[3]
        s = max(pw / sub.width, ph / sub.height)
        cov = sub.resize((int(sub.width * s) + 1, int(sub.height * s) + 1), Image.LANCZOS)
        cover = cov.crop(((cov.width - pw) // 2, (cov.height - ph) // 2,
                          (cov.width - pw) // 2 + pw, (cov.height - ph) // 2 + ph))
        cover = cover.filter(ImageFilter.GaussianBlur(26))
        r_, g_, b_ = cover.split()
        cover = Image.merge("RGB", (r_.point(lambda v: int(v * 0.26)),
                                   g_.point(lambda v: int(v * 0.28)),
                                   b_.point(lambda v: int(v * 0.34))))
        im.paste(cover, (PANEL[0], PANEL[1]))
        im.paste(sub, (px, py))
        d = ImageDraw.Draw(im)
        d.rectangle([PANEL[0], PANEL[1], PANEL[0] + pw, PANEL[1] + ph],
                    outline=ctx.C_BORDER, width=2)
        im.save(pdir / f"{b['name']}.jpg", quality=88)
    if outro:
        card_outro(ctx, outro).save(pdir / f"{len(beats) + 1:02d}-outro.jpg", quality=88)
    print(f"预览静帧：{pdir}")


def build(ctx):
    cfg = ctx.cfg
    beats = [dict(b) for b in cfg["beats"]]
    if cfg.get("intro"):
        intro = dict(cfg["intro"])
        intro["dur"] = round(max(intro.get("min_dur", 3.6),
                                vlen(ctx, intro["voice"], "intro") + 0.45), 2) if cfg["voice"]["enabled"] \
            else max(intro.get("min_dur", 3.6), intro.get("dur", 4.0))
    else:
        intro = None
    if cfg.get("outro"):
        outro = dict(cfg["outro"])
        outro["dur"] = round(max(outro.get("min_dur", 3.6),
                                 vlen(ctx, outro["voice"], "outro") + 0.45), 2) if cfg["voice"]["enabled"] \
            else max(outro.get("min_dur", 3.6), outro.get("dur", 4.0))
    else:
        outro = None

    beats = plan(ctx, beats)
    total = round((intro["dur"] if intro else 0) + sum(b["dur"] for b in beats)
                  + (outro["dur"] if outro else 0), 3)
    print(f"{len(beats)} 拍  总时长 {total:.2f}s  " +
          " ".join(f"{b['name']}={b['dur']:.1f}" for b in beats))

    parts, events = [], []
    t = 0.0
    if intro:
        parts.append(render_card(ctx, card_intro(ctx, intro), intro["dur"], "intro"))
        events.append((0.0, voice_file(ctx, intro["voice"], "intro")))
        t += intro["dur"]
    for i, b in enumerate(beats):
        bg = ctx.build / f"bg-{b['name']}.png"
        beat_bg(ctx, b, i, len(beats)).save(bg)
        part, speed = render_beat(ctx, b, bg)
        if cfg["voice"]["enabled"]:
            events.append((t, voice_file(ctx, b["voice"], b["name"])))
        print(f"  {b['name']} {b['dur']:.2f}s speed={speed:.2f}")
        parts.append(part)
        t += b["dur"]
    if outro:
        parts.append(render_card(ctx, card_outro(ctx, outro), outro["dur"], "outro"))
        events.append((t, voice_file(ctx, outro["voice"], "outro")))

    lst = ctx.build / "parts.txt"
    lst.write_text("".join(f"file '{p.name}'\n" for p in parts), encoding="utf-8")
    silent = ctx.build / "silent.mp4"
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst,
         "-c", "copy", silent])
    got = probe(silent)
    if abs(got - total) > 0.25:
        raise SystemExit(f"拼接后 {got:.2f}s 与规划 {total:.2f}s 不一致")

    voice = mix_audio(ctx, events, total) if cfg["voice"]["enabled"] else None
    out = ctx.out / f"{cfg['out_name']}-{total:.1f}s-1080x1920.mp4"
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", silent]
    if voice:
        cmd += ["-i", voice, "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "192k",
                "-ar", "48000", "-ac", "2"]
    cmd += ["-c:v", "copy", "-movflags", "+faststart", "-t", f"{total:.3f}", out]
    run(cmd)
    print(f"成片：{out}\n规划 {total:.2f}s 实测 {probe(out):.2f}s")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="beats.json")
    ap.add_argument("--preview", action="store_true")
    a = ap.parse_args()
    cfg_path = Path(a.config).resolve()
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    for k, v in DEFAULTS.items():
        cfg.setdefault(k, v)
    for k, v in DEFAULTS["theme"].items():
        cfg["theme"].setdefault(k, v)
    ctx = Ctx(cfg, cfg_path.parent)
    for d in (ctx.build, ctx.audio, ctx.out):
        d.mkdir(parents=True, exist_ok=True)
    beats = cfg["beats"]
    check_beats(ctx, beats)
    if a.preview:
        preview(ctx, cfg.get("intro"), beats, cfg.get("outro"))
        return 0
    build(ctx)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
