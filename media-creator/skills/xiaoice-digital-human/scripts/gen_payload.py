#!/usr/bin/env python3
"""生成小冰视频提交 JSON，自动完成画布适配。

最容易踩的坑是虚拟人宽高写死 —— 官方明确要求 attributes 的宽高必须与所选姿态的
previewPicture 保持原始宽高比，否则生成的视频里虚拟人会被拉伸变形。而不同形象的
姿态图尺寸并不一致（实测有 720x1280、944x1080、2160x3840 等），所以必须动态计算。

用法:
    python gen_payload.py --avatar VHPVCW35N3M8DO0 --text "大家好" --out payload.json
    python gen_payload.py --avatar VHPVCW35N3M8DO0 --text "..." --canvas 1080x1920
    python gen_payload.py --avatar ... --text "..." --has-latex --caption --art-font MHM_1

依赖: 仅标准库。
"""
import argparse
import json
import os
import re
import urllib.error
import urllib.request


DEFAULT_BASE = "https://aibeings-vip.xiaoice.com"


def call(base, key, path, body=None, method="POST"):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(base + path, data=data, method=method)
    req.add_header("subscription-key", key)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=40) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise SystemExit("HTTP %s: %s" % (exc.code, exc.read().decode("utf-8", "replace")[:300]))
    if payload.get("code") != 200:
        raise SystemExit("业务失败 code=%s message=%s" % (payload.get("code"), payload.get("message")))
    return payload["data"]


def parse_dims(url):
    """从姿态预览图 URL 解析原始宽高，形如 .../xxxx_2160x3840.webp"""
    base = (url or "").rsplit("/", 1)[-1]
    m = re.search(r"_(\d+)x(\d+)\.[A-Za-z0-9]+$", base)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def even(n):
    n = max(2, int(round(n)))
    return n + 1 if n % 2 else n


def fit_canvas(src_w, src_h, canvas_w, canvas_h):
    """等比缩放并居中；官方文档例子：1080x1920 画布 + 944x1080 姿态图 -> 1080x1236 @ (0,342)"""
    if not src_w or not src_h:
        return canvas_w, canvas_h, 0, 0
    scale = min(canvas_w / src_w, canvas_h / src_h)
    w, h = even(src_w * scale), even(src_h * scale)
    return w, h, (canvas_w - w) // 2, (canvas_h - h) // 2


def main():
    ap = argparse.ArgumentParser(description="生成小冰视频提交 JSON（自动画布适配）")
    ap.add_argument("--avatar", required=True, help="形象 bizId（来自 queryDigitalEmployee）")
    ap.add_argument("--text", required=True, help="播报文本；含公式时用 $...$ 包裹")
    ap.add_argument("--out", default="payload.json", help="输出文件，默认 payload.json")
    ap.add_argument("--canvas", default="1080x1920", help="画布尺寸，默认 1080x1920（竖屏）")
    ap.add_argument("--posture", help="指定姿态 bizId，缺省用第一个")
    ap.add_argument("--voice", help="指定 voiceId，缺省用形象默认声音")
    ap.add_argument("--name", help="视频名称，默认 output-name")
    ap.add_argument("--has-latex", action="store_true", help="按 LaTeX 处理文本（含公式时加）")
    ap.add_argument("--caption", action="store_true", help="开启字幕")
    ap.add_argument("--art-font", help="花字模板名，如 MHM_1（用于第一个文字素材）")
    ap.add_argument("--display-text", help="叠加文字素材内容（配合 --art-font）")
    ap.add_argument("--transition", help="转场类型，如 wipe_left")
    ap.add_argument("--bg-music", help="全局背景音乐 URL（MP3/WAV，<=50MB）")
    ap.add_argument("--bg-image", help="场景背景图 URL（JPG/PNG/GIF，<=10MB）")
    ap.add_argument("--base", default=os.environ.get("BASE", DEFAULT_BASE),
                    help="Base URL，默认取环境变量 BASE")
    ap.add_argument("--key", default=os.environ.get("XIAOICE_KEY", ""), help="订阅密钥")
    args = ap.parse_args()

    if not args.key:
        raise SystemExit("缺少密钥：请设置环境变量 XIAOICE_KEY 或用 --key 传入")

    canvas_w, canvas_h = (int(v) for v in args.canvas.lower().split("x"))
    if (canvas_w * canvas_h) > 3840 * 2160:
        raise SystemExit("画布超过约束 width * height <= 3840 * 2160")

    detail = call(args.base, args.key, "/openapi/video/detailDigitalEmployee", {"bizId": args.avatar})

    vh = detail.get("virtualHumanId")
    postures = detail.get("postureInfos") or []
    voices = detail.get("voiceInfos") or []
    if not vh:
        raise SystemExit("该形象缺少 virtualHumanId")

    posture = next((p for p in postures if p.get("bizId") == args.posture), None) or (postures[0] if postures else None)
    if not posture:
        raise SystemExit("该形象没有可用姿态")
    voice = args.voice or detail.get("defaultVoiceId") or (voices[0]["voiceId"] if voices else None)
    if not voice:
        raise SystemExit("该形象没有可用声音")

    src = parse_dims(posture.get("previewPicture"))
    w, h, x, y = fit_canvas(*(src or (0, 0)), canvas_w, canvas_h)
    if src:
        print("姿态 %s 预览图 %dx%d -> 画布内 %dx%d at (%d,%d)" % (posture["bizId"], src[0], src[1], w, h, x, y))
    else:
        print("警告：未能从预览图解析尺寸，已退回铺满画布（9:16 姿态图时正确）")

    scene = {
        "virtualHuman": {
            "virtualHumanId": vh,
            "virtualHumanPostureId": posture["bizId"],
            "zIndex": 20,
            "attributes": {"width": w, "height": h, "x": x, "y": y},
        },
        "tts": {"voiceId": voice, "rate": 1, "pitch": 1, "volume": 50},
        "voiceTexts": [args.text],
    }

    if args.has_latex:
        scene["hasLatex"] = True
        scene["tts"]["latexStyle"] = {"fontSize": 48, "fontColor": "#FFDE00"}
    if args.caption:
        scene["caption"] = {"topCenter": True, "zIndex": 60,
                            "attributes": {"fontSize": 40, "fontColor": "#ffffff", "bold": True}}
    if args.display_text:
        item = {"content": args.display_text, "zIndex": 30,
                "attributes": {"x": 100, "y": 200, "fontSize": 72, "font": 6, "fontColor": "#FFDE00", "bold": True}}
        if args.art_font:
            item["artFontTemplateName"] = args.art_font
        scene["displayTexts"] = [item]
    if args.transition:
        scene["transferEffects"] = [{"type": args.transition, "duration": 1}]
    if args.bg_image:
        scene["backgroundImage"] = {"mediaUrl": args.bg_image}

    creation = {"scenes": [scene]}
    if args.bg_music:
        creation["backgroundMusic"] = {"mediaUrl": args.bg_music, "volume": 0.2, "loop": True}

    payload = {
        "outputVideoName": args.name or "output-name",
        "outputVideoFormat": "mp4",
        "width": canvas_w,
        "height": canvas_h,
        "aigcWatermark": False,
        "creationDetail": creation,
    }

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    print("已写入 %s" % args.out)
    print()
    print("提交：")
    print('  curl -s -X POST "$BASE/openapi/video/task/v2/submit" \\')
    print('    -H "Content-Type: application/json" -H "subscription-key: $XIAOICE_KEY" \\')
    print('    --data-binary @%s' % args.out)


if __name__ == "__main__":
    main()
