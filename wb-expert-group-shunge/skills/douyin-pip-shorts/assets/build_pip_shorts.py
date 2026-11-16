# -*- coding: utf-8 -*-
"""配置驱动的本地竖屏画中画合成器（Python 3.8+、ffmpeg）。"""
import argparse
import json
import math
import subprocess
import sys
from pathlib import Path


def number(value, label, minimum=0, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{label}必须为有限数值")
    if value < minimum or (positive and value == minimum):
        raise ValueError(f"{label}超出有效范围")
    return value


def load_config(path, output):
    if any(str(p).replace("\\", "/").startswith("//") for p in (path, output)):
        raise ValueError("不接受网络共享路径")
    path = path.resolve()
    c = json.loads(path.read_text(encoding="utf-8"))
    inputs = [path]

    def source(value):
        if not isinstance(value, str) or not value or "://" in value or value.replace("\\", "/").startswith("//"):
            raise ValueError("素材必须是本地文件路径")
        result = (path.parent / value).resolve()
        if not result.is_file():
            raise ValueError(f"素材不存在：{result}")
        inputs.append(result)
        return result

    def voice(node):
        node["voice"] = source(node["voice"])
        number(node["voice_duration"], "旁白时长", positive=True)

    layout = c["layout"]
    for key in ("width", "height", "pip_width"):
        value = number(layout[key], key, positive=True)
        if not isinstance(value, int) or value % 2:
            raise ValueError(f"{key}必须是正偶数整数")
    number(layout["fps"], "帧率", positive=True)
    number(layout["pip_bottom"], "浮窗底边距")
    if number(layout["pip_alpha"], "透明度") > 1 or layout["pip_width"] > layout["width"]:
        raise ValueError("透明度必须不大于1，浮窗不能超出画布宽")
    sub = c["subtitles"]
    if not isinstance(sub["font"], str) or not sub["font"] or any(x in sub["font"] for x in ",\r\n{}\\"):
        raise ValueError("字体名称含非法字符")
    for key in ("tag_size", "size", "full_margin", "pip_margin", "hold"):
        number(sub[key], key)
    timing = c["timing"]
    for key in ("target", "tail"):
        number(timing[key], key, positive=True)
    for key in ("pause", "ops_lead", "voice_lead", "chapter_gap"):
        number(timing[key], key)
    for node in (c.get("intro"), c.get("outro")):
        if node:
            if node["kind"] not in ("card", "anim"):
                raise ValueError("片头片尾kind必须为card或anim")
            node["src"] = source(node["src"])
            number(node["dur"], "卡片时长", positive=True)
            if node.get("voice"):
                voice(node)
                if node["voice_duration"] > node["dur"]:
                    raise ValueError("卡片旁白长于卡片")
    if not c["base"] or not c["beats"]:
        raise ValueError("底板片段和拍数必须非零")
    for item in c["base"]:
        item["src"] = source(item["src"])
        number(item["start"], "底板起点")
        number(item["duration"], "底板时长", positive=True)
    c["recording"] = source(c["recording"])
    voice(c["background"])
    chapters = timing["chapters"]
    if isinstance(chapters, bool) or not isinstance(chapters, int) or not 1 <= chapters <= len(c["beats"]):
        raise ValueError("章节数必须在1与拍数之间")
    for b in c["beats"]:
        voice(b)
        crop = b["crop"]
        if len(crop) != 4 or any(not isinstance(x, int) or isinstance(x, bool) for x in crop):
            raise ValueError("crop必须是四个整数：宽、高、x、y")
        for j, value in enumerate(crop):
            number(value, "裁剪坐标", positive=j < 2)
        if pip_height(c, b) + layout["pip_bottom"] > layout["height"]:
            raise ValueError("浮窗高度超出画布")
        number(b["t_in"], "录屏起点")
        number(b["t_out"], "录屏终点", minimum=b["t_in"], positive=True)
        for key in ("sub", "tag"):
            if not isinstance(b[key], str):
                raise ValueError("字幕和标签必须为字符串")
    for text, start, end in c["background"]["subs"]:
        if not isinstance(text, str):
            raise ValueError("背景字幕必须为字符串")
        number(start, "字幕起点")
        if end is not None:
            number(end, "字幕终点", minimum=start, positive=True)
    output = output.resolve()
    if output.exists():
        raise ValueError(f"输出目录已存在，拒绝覆盖：{output}")
    # resolve同时处理符号链接；新输出不能包含输入，也不能位于素材目录中。
    for item in inputs:
        if output == item or output == item.parent or item.parent in output.parents or output in item.parents:
            raise ValueError(f"输出目录必须独立于配置和素材目录：{item.parent}")
    if not output.parent.is_dir():
        raise ValueError("输出父目录必须已存在")
    return c, output


def pip_height(c, beat):
    height = round(c["layout"]["pip_width"] * beat["crop"][1] / beat["crop"][0])
    return max(2, height - height % 2)


def plan(c):
    t = c["timing"]
    intro = c.get("intro") or {}
    outro = c.get("outro") or {}
    middle = t["target"] - intro.get("dur", 0) - outro.get("dur", 0)
    ops = t["pause"] + c["background"]["voice_duration"] - t["ops_lead"]
    count = len(c["beats"])
    # 明确分配章节边界，避免ceil分组少插过渡导致预算漂移。
    boundaries = {count * i // t["chapters"] for i in range(1, t["chapters"])}
    span = middle - ops - t["tail"] - len(boundaries) * t["chapter_gap"]
    dwell = math.floor(span / count * 100) / 100
    if ops < 0 or dwell < 1.4:
        raise ValueError("固定节点挤占时间，每拍不足1.4秒；减少节点或拍数")
    slots, beats = [], []
    if ops:
        slots.append((0, ops, None))
    current, previous = ops, t["pause"] + c["background"]["voice_duration"] + 0.05
    offset = intro.get("dur", 0)
    for i, original in enumerate(c["beats"]):
        if i in boundaries:
            if t["chapter_gap"]:
                slots.append((current, t["chapter_gap"], None))
            current += t["chapter_gap"]
        voice_start = max(current - t["voice_lead"], previous)
        if voice_start + original["voice_duration"] > current + dwell:
            raise ValueError(f"第{i + 1}拍旁白装不进窗口，请缩短旁白或减少拍数")
        beat = dict(original, start=offset + current, voice_start=offset + voice_start, dur=dwell)
        beats.append(beat)
        slots.append((current, dwell, beat))
        previous = voice_start + original["voice_duration"] + 0.1
        current += dwell
    slots.append((current, t["tail"], None))
    middle = current + t["tail"]
    if sum(b["duration"] for b in c["base"]) < middle:
        raise ValueError("底板素材时长不足")
    return dict(slots=slots, beats=beats, middle=middle, intro=offset,
                total=offset + middle + outro.get("dur", 0))


def run(args, cwd=None):
    result = subprocess.run([str(x) for x in args], cwd=cwd, capture_output=True, text=True)
    if result.returncode:
        raise ValueError(f"媒体命令失败：{result.stderr[-2000:]}")
    return result


def probe(path):
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                      "-of", "csv=p=0", path]).stdout.strip())


def validate_media(c):
    # 仅真实执行时实测；dry-run只使用配置内显式声明的时长，不启动ffprobe。
    cache = {}

    def duration(path):
        if path not in cache:
            cache[path] = probe(path)
        return cache[path]

    for node in [c["background"], *c["beats"], c.get("intro"), c.get("outro")]:
        if node and node.get("voice"):
            if abs(duration(node["voice"]) - node["voice_duration"]) > 0.08:
                raise ValueError(f"旁白实测与配置不符，请更新voice_duration：{node['voice']}")
    for item in c["base"]:
        if item["start"] + item["duration"] > duration(item["src"]) + 0.05:
            raise ValueError("底板取段超出素材时长")
    for beat in c["beats"]:
        if beat["t_out"] > duration(c["recording"]) + 0.05:
            raise ValueError("录屏取段超出素材时长")
    for node in (c.get("intro"), c.get("outro")):
        if node and node["kind"] == "anim" and node["dur"] > duration(node["src"]) + 0.05:
            raise ValueError("动效卡片时长超出素材")


def stamp(seconds):
    centiseconds = round(seconds * 100)
    hours, rest = divmod(centiseconds, 360000)
    minutes, rest = divmod(rest, 6000)
    return f"{hours}:{minutes:02d}:{rest / 100:05.2f}"


def markup(text):
    # 禁止输入注入ASS控制码；只支持约定的{金色高亮}与换行。
    text = text.replace("\\", "＼").replace("\r", "").replace("\n", r"\N")
    return "".join(r"{\c&H4DC9FF&}" if ch == "{" else r"{\c&HFFFFFF&}" if ch == "}" else ch for ch in text)


def make_ass(c, p):
    l, sub = c["layout"], c["subtitles"]
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {l['width']}
PlayResY: {l['height']}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Tag,{sub['font']},{sub['tag_size']},&H00FFFFFF,&H000000FF,&H00000000,&H99000000,-1,0,0,0,100,100,1,0,3,9,0,2,60,60,0,1
Style: Sub,{sub['font']},{sub['size']},&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,1,0,1,4,1,2,60,60,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []

    def event(start, end, style, margin, text):
        end = min(end, p["total"])
        if end > start:
            lines.append(f"Dialogue: 0,{stamp(start)},{stamp(end)},{style},,0,0,{int(margin)},,{markup(text)}")

    bg0 = p["intro"] + c["timing"]["pause"]
    bg_end = min(bg0 + c["background"]["voice_duration"] + 0.2, p["beats"][0]["voice_start"] - 0.05)
    for text, start, end in c["background"]["subs"]:
        event(bg0 + start, min(bg_end, bg0 + end) if end is not None else bg_end,
              "Sub", sub["full_margin"], text)
    for i, b in enumerate(p["beats"]):
        top = pip_height(c, b) + l["pip_bottom"]
        event(b["start"], b["start"] + b["dur"], "Tag", top - 30, b["tag"])
        end = b["voice_start"] + b["voice_duration"] + sub["hold"]
        if i + 1 < len(p["beats"]):
            end = min(end, p["beats"][i + 1]["voice_start"] - 0.05)
        event(b["voice_start"], end, "Sub", top + sub["pip_margin"], b["sub"])
    return header + "\n".join(lines) + "\n"


def render(c, p, output):
    l = c["layout"]
    w, h, fps = l["width"], l["height"], l["fps"]
    build = output / "build"
    build.mkdir()
    norm = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1,fps={fps}"
    prefix = ["ffmpeg", "-n", "-v", "error"]
    codec = ["-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p"]

    def concat(parts, name):
        listing = build / f"{name}.txt"
        listing.write_text("".join(f"file '{item.name}'\n" for item in parts), encoding="utf-8")
        result = build / f"{name}.mp4"
        run([*prefix, "-f", "concat", "-safe", "1", "-i", listing, "-c", "copy", result])
        return result

    base_parts, left = [], p["middle"]
    for i, item in enumerate(c["base"]):
        take = min(item["duration"], left)
        if take <= 0:
            break
        dest = build / f"base-{i}.mp4"
        run([*prefix, "-ss", item["start"], "-i", item["src"], "-t", take, "-vf", norm, *codec, dest])
        base_parts.append(dest)
        left -= take
    base = concat(base_parts, "base")
    parts = []

    def card(node, name):
        dest = build / f"{name}.mp4"
        loop = ["-loop", "1"] if node["kind"] == "card" else []
        run([*prefix, *loop, "-i", node["src"], "-t", node["dur"], "-vf", norm, *codec, dest])
        parts.append(dest)

    if c.get("intro"):
        card(c["intro"], "intro")
    for i, (start, duration, beat) in enumerate(p["slots"]):
        dest = build / f"slot-{i}.mp4"
        args = [*prefix, "-ss", start, "-i", base]
        if beat:
            cw, ch, cx, cy = beat["crop"]
            speed = (beat["t_out"] - beat["t_in"]) / duration
            fc = (f"[0:v]setpts=PTS-STARTPTS,setsar=1,fps={fps}[bg];"
                  f"[1:v]crop={cw}:{ch}:{cx}:{cy},scale={l['pip_width']}:{pip_height(c, beat)},"
                  f"setsar=1,setpts=(PTS-STARTPTS)/{speed},fps={fps},format=yuva420p,"
                  f"colorchannelmixer=aa={l['pip_alpha']},drawbox=x=0:y=0:w=iw:h=ih:color=black@0.3:t=2[pip];"
                  f"[bg][pip]overlay={(w-l['pip_width'])//2}:main_h-overlay_h-{l['pip_bottom']}:"
                  "format=auto,setsar=1[v]")
            args += ["-ss", beat["t_in"], "-t", beat["t_out"] - beat["t_in"], "-i", c["recording"],
                     "-filter_complex", fc, "-map", "[v]"]
        else:
            args += ["-vf", f"setsar=1,fps={fps}"]
        run([*args, "-t", duration, "-r", fps, *codec, dest])
        parts.append(dest)
    if c.get("outro"):
        card(c["outro"], "outro")
    silent = concat(parts, "silent")
    events = [(p["intro"] + c["timing"]["pause"], c["background"]["voice"])]
    events += [(b["voice_start"], b["voice"]) for b in p["beats"]]
    for node, start in ((c.get("intro"), 0), (c.get("outro"), p["intro"] + p["middle"])):
        if node and node.get("voice"):
            events.append((start, node["voice"]))
    args = [*prefix, "-i", silent, "-f", "lavfi", "-t", p["total"], "-i", "anullsrc=r=48000:cl=stereo"]
    filters = []
    for i, (start, voice) in enumerate(events, 2):
        args += ["-i", voice]
        delay = round(start * 1000)
        filters.append(f"[{i}:a]aformat=sample_fmts=fltp:channel_layouts=stereo,aresample=48000,adelay={delay}|{delay}[a{i}]")
    filters.append("[1:a]" + "".join(f"[a{i}]" for i in range(2, 2 + len(events))) +
                   f"amix=inputs={len(events)+1}:normalize=0:dropout_transition=0,alimiter=limit=0.95,atrim=0:{p['total']}[audio]")
    # 固定相对字幕名避免Windows盘符、引号进入libavfilter路径表达式。
    run([*args, "-filter_complex", ";".join(filters), "-map", "0:v", "-map", "[audio]",
         "-vf", "subtitles=subtitles.ass", "-t", p["total"], "-c:v", "libx264", "-preset", "medium",
         "-crf", "19", "-pix_fmt", "yuv420p", "-r", fps, "-c:a", "aac", "-b:a", "192k",
         "-movflags", "+faststart", output / "video.mp4"], cwd=output)
    if abs(probe(output / "video.mp4") - p["total"]) > 0.2:
        raise ValueError("成片实测时长偏离规划，保留输出供检查，下一次须换新目录")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path, help="本地JSON配置；素材相对它解析")
    parser.add_argument("--output-dir", required=True, type=Path, help="独立且尚不存在的输出目录")
    parser.add_argument("--dry-run", action="store_true", help="只验证配置并打印规划；零写入、零子进程")
    parser.add_argument("--subs-only", action="store_true", help="仅在新输出目录生成字幕，不启动媒体程序")
    args = parser.parse_args(argv)
    try:
        c, output = load_config(args.config, args.output_dir)
        p = plan(c)
        subtitles = make_ass(c, p)
        print(json.dumps({"total": p["total"], "middle": p["middle"], "beats": p["beats"],
                          "output": str(output), "duration_source": "配置声明值"}, ensure_ascii=False, default=str, indent=2))
        if args.dry_run:
            return 0
        if not args.subs_only:
            validate_media(c)
        output.mkdir(exist_ok=False)
        (output / "subtitles.ass").write_text(subtitles, encoding="utf-8")
        if not args.subs_only:
            render(c, p, output)
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    sys.exit(main())
