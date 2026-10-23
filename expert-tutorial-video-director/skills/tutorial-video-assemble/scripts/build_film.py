# -*- coding: utf-8 -*-
"""系列教程视频：配音 + 讲义卡片 + 剪辑配置 + 字幕，一条命令。

用法：
    python build_film.py --ep <集目录>                  # 只生成 build/ 产物
    python build_film.py --ep <集目录> --render         # 生成后直接渲染出片
    python build_film.py --ep <集目录> --force          # 忽略配音缓存，全部重录
    python build_film.py --ep <集目录> --subs           # 烧字幕（默认不烧）
    python build_film.py --ep <集目录> --fit stretch     # 配音超长时自动降速画面兜住
    python build_film.py --ep <集目录> --preset 9:16     # 临时覆盖画布

输入：<集目录>/beats.json（分镜 + 台词 + 画布）
产物：
    build/audio/<id>.mp3|wav     逐段配音（wav 已响度归一）
    build/clips/<id>.mp4         讲义卡片片段（静帧，时长=配音+尾部停顿）
    build/config.json            交给 video_pipeline.py render
    build/plan.csv               每段槽位/配音/余量/判定
    build/<EP>_台词稿.md          带时间码的台词稿（交付物）

画布：
    beats.json 里 "canvas": {"preset": "9:16"} 或 {"width":1080,"height":1920}。
    预设表在 ../svg-lecture-deck/scripts/canvas.py，横屏/竖屏/方形/4K 都走同一套令牌。
    缺省 16:9 = 1920×1080，与旧项目完全一致。
"""
import argparse
import asyncio
import csv
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILLS_ROOT = HERE.parents[1]              # .../skills
DECK_SCRIPTS = SKILLS_ROOT / "svg-lecture-deck" / "scripts"

try:
    sys.path.insert(0, str(DECK_SCRIPTS))
    import canvas as canvas_mod           # noqa: E402
except Exception:                          # 单独拷走本技能时的降级
    canvas_mod = None

DEFAULT_FFMPEG = r"C:/ffmpeg/bin/ffmpeg.exe"
DEFAULT_FFPROBE = r"C:/ffmpeg/bin/ffprobe.exe"
LOUDNORM = "loudnorm=I=-16:TP=-1.5:LRA=11"
MAX_CUE = 26          # 单条字幕最多字数
GAP = 0.015           # 段内配音余量


# ---------------------------------------------------------------- 外部工具
def find_bin(explicit, default, name):
    p = Path(explicit or default)
    if not p.exists():
        raise SystemExit("找不到 %s：%s（用 --%s 指定）" % (name, p, name))
    return str(p)


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("命令失败：%s\n%s" % (" ".join(map(str, cmd))[:400], (r.stderr or "")[-800:]))
    return r


def duration(ffprobe, path):
    out = run([ffprobe, "-v", "error", "-show_entries", "format=duration",
               "-of", "default=noprint_wrappers=1:nokey=1", str(path)]).stdout.strip()
    try:
        return float(out)
    except ValueError:
        raise SystemExit("读不到时长：%s" % path)


def resolve_canvas(cfg, preset_override=None):
    cfg = dict(cfg or {})
    if preset_override:
        cfg = {"preset": preset_override}
    if canvas_mod:
        return canvas_mod.resolve(cfg)
    w, h = cfg.get("width"), cfg.get("height")
    if not w or not h:
        if cfg.get("preset") and cfg["preset"] not in ("16:9",):
            raise SystemExit("画布预设需要同包的 svg-lecture-deck 技能，"
                             "或在 beats.json 里直接写 width/height")
        w, h = 1920, 1080
    return int(w) - int(w) % 2, int(h) - int(h) % 2


def sub_size(w, h):
    if canvas_mod:
        return canvas_mod.subtitle_size(w, h)
    return max(16, int(round(min(w, h) * 0.045)))


# ---------------------------------------------------------------- 台词与字幕
_TERM = re.compile(r"(?<=[。！？!?；;…])")
_COMMA = re.compile(r"(?<=[，,、：:])")


def split_cues(text, max_chars=MAX_CUE):
    """按句末标点切句，过长再按逗号切，仍过长按字数硬切。"""
    text = (text or "").strip()
    if not text:
        return []
    cues = []
    for sent in [s.strip() for s in _TERM.split(text) if s.strip()]:
        if len(sent) <= max_chars:
            cues.append(sent)
            continue
        buf = ""
        for piece in [s for s in _COMMA.split(sent) if s.strip()]:
            if len(buf) + len(piece) <= max_chars:
                buf += piece
                continue
            if buf:
                cues.append(buf)
                buf = piece
            else:
                while len(piece) > max_chars:
                    cues.append(piece[:max_chars])
                    piece = piece[max_chars:]
                buf = piece
        if buf:
            cues.append(buf)
    return cues


def cues_with_time(text, span):
    """把一段配音按字数比例摊到 [0, span] 上。span 为配音实际时长。"""
    cues = split_cues(text)
    if not cues or span <= 0:
        return []
    total = sum(len(c) for c in cues) or 1
    out, t = [], 0.0
    for c in cues:
        d = span * len(c) / total
        s, e = round(t, 3), round(t + max(0.35, d) - GAP, 3)
        out.append({"start": s, "end": e, "text": c})
        t += d
    return out


# ---------------------------------------------------------------- 素材生成
def make_voice(ffmpeg, aud: Path, bid, text, voice, rate, volume, loudnorm, force):
    mp3, wav = aud / (bid + ".mp3"), aud / (bid + ".wav")
    if force or not (mp3.exists() and mp3.stat().st_size > 0):
        if not text.strip():
            raise SystemExit("段 %s 没有台词，无法配音。" % bid)
        import edge_tts
        asyncio.run(edge_tts.Communicate(text, voice, rate=rate, volume=volume).save(str(mp3)))
    if force or not (wav.exists() and wav.stat().st_size > 0):
        run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(mp3),
             "-af", loudnorm, "-ar", "48000", "-ac", "1", str(wav)])
    return wav


def make_silence(ffmpeg, aud: Path, bid, seconds):
    wav = aud / (bid + ".wav")
    if not wav.exists():
        run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
             "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono",
             "-t", "%.3f" % max(0.2, seconds), "-c:a", "pcm_s16le", str(wav)])
    return wav


def card_clip(ffmpeg, clips: Path, png: Path, seconds, fps, name):
    out = clips / (name + ".mp4")
    run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
         "-loop", "1", "-framerate", str(fps), "-i", str(png),
         "-t", "%.3f" % seconds, "-r", str(fps),
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
         "-pix_fmt", "yuv420p", str(out)])
    return out


def render_card_svg(svg: Path, png_dir: Path, w, h):
    script = DECK_SCRIPTS / "svg2png.py"
    if not script.exists():
        raise SystemExit("缺 %s：卡片 SVG 渲染脚本在 svg-lecture-deck 技能里，"
                         "两个技能要一起装" % script)
    run([sys.executable, str(script), "--file", str(svg), "--out-dir", str(png_dir),
         "--width", str(w), "--height", str(h)])


# ---------------------------------------------------------------- 主流程
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ep", required=True, help="集目录（含 beats.json）")
    ap.add_argument("--beats", help="自定义 beats 路径，默认 <ep>/beats.json")
    ap.add_argument("--ffmpeg", default=DEFAULT_FFMPEG)
    ap.add_argument("--ffprobe", default=DEFAULT_FFPROBE)
    ap.add_argument("--preset", help="临时覆盖画布：16:9 / 9:16 / 1:1 / 4:5 / 3:4 / 4k")
    ap.add_argument("--force", action="store_true", help="忽略配音/归一缓存")
    ap.add_argument("--subs", action="store_true", help="烧字幕（同时导出 SRT）")
    ap.add_argument("--fit", choices=["strict", "stretch"], default="strict",
                    help="配音超出槽位时：strict 只报警，stretch 自动降速画面")
    ap.add_argument("--render", action="store_true", help="生成后立刻渲染成片")
    a = ap.parse_args()

    ffmpeg = find_bin(a.ffmpeg, DEFAULT_FFMPEG, "ffmpeg")
    ffprobe = find_bin(a.ffprobe, DEFAULT_FFPROBE, "ffprobe")

    ep_dir = Path(a.ep).resolve()
    beats_path = Path(a.beats) if a.beats else ep_dir / "beats.json"
    cfg_in = json.loads(beats_path.read_text(encoding="utf-8"))

    canvas_cfg = cfg_in.get("canvas", {})
    W, H = resolve_canvas(canvas_cfg, a.preset)
    FPS = int(canvas_cfg.get("fps", 30))
    v = cfg_in.get("voice", {})
    VOICE = v.get("name", "zh-CN-YunxiNeural")
    RATE = v.get("rate", "+8%")
    VOLUME = v.get("volume", "+0%")
    NORM = cfg_in.get("loudnorm", LOUDNORM)
    TAIL = float(cfg_in.get("card_tail", 0.9))
    EP = cfg_in.get("episode", ep_dir.name)

    cards_dir = (ep_dir / cfg_in.get("cards_dir", "cards")).resolve()
    png_dir = (ep_dir / cfg_in.get("cards_png_dir", "cards_png")).resolve()
    rec_dir = (ep_dir / cfg_in.get("rec_dir", "rec")).resolve()
    build = ep_dir / "build"
    aud, clips = build / "audio", build / "clips"
    aud.mkdir(parents=True, exist_ok=True)
    if clips.exists():
        shutil.rmtree(clips)
    clips.mkdir(parents=True)

    print("画布 %d×%d @%dfps" % (W, H, FPS))

    rows, segs, script = [], [], []
    t_cursor = 0.0
    over, missing = [], []

    for b in cfg_in.get("beats", []):
        bid, kind = b["id"], b.get("kind", "card")
        text = b.get("text", "")

        if text.strip():
            wav = make_voice(ffmpeg, aud, bid, text, VOICE, RATE, VOLUME, NORM, a.force)
            voice = duration(ffprobe, wav)
        else:
            voice = 0.0
            wav = None

        if kind == "card":
            png = png_dir / b["png"]
            if not png.exists():
                svg = cards_dir / (Path(b["png"]).stem + ".svg")
                if svg.exists():
                    render_card_svg(svg, png_dir, W, H)
                else:
                    missing.append(str(b["png"]))
                    continue
            slot = round(voice + TAIL, 2) if voice else float(b.get("seconds", 3.0))
            clip = card_clip(ffmpeg, clips, png, slot, FPS, bid)
            cdur = duration(ffprobe, clip)
            seg = {"source": str(clip), "start": 0.0, "end": round(cdur - 0.002, 3)}
            real = seg["end"]
        else:
            src = Path(b["src"])
            src_path = src if src.is_absolute() else (rec_dir / src)
            if not src_path.exists():
                missing.append(str(src_path))
                continue
            total = duration(ffprobe, src_path)
            s = float(b.get("start", 0.0))
            e = float(b.get("end", total))
            if not (0 <= s < e <= total + 0.05):
                raise SystemExit("段 %s 范围越界：%.3f~%.3f，源只有 %.3f 秒" % (bid, s, e, total))
            e = min(e, total)
            speed = float(b.get("speed", 1.0))
            if voice and a.fit == "stretch" and voice > (e - s) / speed - 0.15:
                speed = round((e - s) / (voice + 0.25), 3)
            speed = max(0.05, speed)
            slot = round((e - s) / speed, 2)
            seg = {"source": str(src_path), "start": round(s, 3), "end": round(e, 3), "speed": speed}
            real = slot

        if wav:
            seg["voice_file"] = str(wav)
            if a.subs:
                seg["subtitles"] = cues_with_time(text, min(voice, real))
        else:
            make_silence(ffmpeg, aud, bid, real)
            seg["voice_file"] = str(aud / (bid + ".wav"))

        margin = round(real - voice, 2)
        fit = "OK" if voice == 0 or margin >= 0.15 else "OVER"
        if fit == "OVER":
            over.append((bid, voice, real))
        segs.append(seg)
        rows.append({"id": bid, "kind": kind, "slot": round(real, 2), "voice": round(voice, 2),
                     "margin": margin, "chars": len(text), "fit": fit,
                     "start": round(t_cursor, 2)})
        script.append((bid, t_cursor, real, voice, text))
        t_cursor += real

    # 配置里的路径一律相对 config.json 所在目录（build/）
    for s in segs:
        s["source"] = Path(_rel(Path(s["source"]), build)).as_posix()
        s["voice_file"] = Path(_rel(Path(s["voice_file"]), build)).as_posix()

    cfg = {"width": W, "height": H, "fps": FPS, "crf": 20,
           "resize_mode": "contain", "audio_mode": "replace",
           "subtitle_mode": "burn" if a.subs else "none",
           "font": cfg_in.get("font", "Microsoft YaHei"),
           "font_size": int(cfg_in.get("font_size", sub_size(W, H))),
           "segments": segs}
    (build / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")

    with (build / "plan.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["id", "kind", "start", "slot", "voice",
                                          "margin", "chars", "fit"])
        w.writeheader()
        w.writerows(rows)

    md = ["# %s 台词稿\n" % cfg_in.get("title", EP),
          "画布 %d×%d，总时长约 %s\n" % (W, H, hhmmss(t_cursor))]
    for bid, st, rl, vd, text in script:
        md.append("**[%s] %s**（%.1fs）\n\n%s\n" % (hhmmss(st), bid, rl, text or "（无台词）"))
    (build / ("%s_台词稿.md" % EP)).write_text("\n".join(md), encoding="utf-8")

    print("%-6s %-5s %7s %7s %7s %5s  %s" % ("段", "类型", "槽位", "配音", "余量", "字数", "判定"))
    for r in rows:
        print("%-6s %-5s %7.2f %7.2f %7.2f %5d  %s" % (r["id"], r["kind"], r["slot"], r["voice"],
                                                      r["margin"], r["chars"], r["fit"]))
    print("总时长 %.2fs（%s）｜配音 %.2fs" % (t_cursor, hhmmss(t_cursor),
                                            sum(r["voice"] for r in rows)))
    if missing:
        print("[缺失素材]", len(missing))
        for m in missing:
            print("   ", m)
    if over:
        print("[配音超出槽位] %d 段，建议加字/提速/--fit stretch：" % len(over))
        for bid, vd, rl in over:
            print("    %s 配音 %.2fs > 槽位 %.2fs" % (bid, vd, rl))
    print("配置:", build / "config.json")

    if a.render:
        out_dir = ep_dir / "out"
        out_dir.mkdir(parents=True, exist_ok=True)
        cmd = [sys.executable, str(HERE / "video_pipeline.py"),
               "--ffmpeg", ffmpeg, "--ffprobe", ffprobe, "render",
               "--config", str(build / "config.json"),
               "--output", str(out_dir / ("%s_render" % EP))]
        print("渲染中 ...")
        run(cmd)
        print("成片目录:", out_dir / ("%s_render" % EP))

    return 2 if (over or missing) else 0


def _rel(p: Path, base: Path) -> str:
    import os
    return os.path.relpath(str(p.resolve()), str(base.resolve()))


def hhmmss(s: float) -> str:
    s = int(round(s))
    return "%02d:%02d" % (s // 60, s % 60)


if __name__ == "__main__":
    raise SystemExit(main())
