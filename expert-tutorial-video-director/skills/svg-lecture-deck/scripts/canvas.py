# -*- coding: utf-8 -*-
"""画布预设与尺寸令牌。

所有尺寸都从「短边 1080」推：
    u = min(W, H) / 1080
1920×1080 时 u = 1，和没有这个模块之前完全一致（老项目不会变样）。
竖屏 1080×1920 时 u = 1，字号的绝对像素不变，但画布窄了，所以文案要写短——
这是内容规则，见 svg-lecture-deck 的画布与版式。

PPT 尺寸换算：144 px = 1 inch。1920×1080 → 13.333×7.5 in（标准 16:9 幻灯片）。
"""
import sys

PRESETS = {
    "16:9": (1920, 1080),   # 横屏教程、B 站/YouTube
    "9:16": (1080, 1920),   # 竖屏短视频、抖音/视频号
    "1:1": (1440, 1440),    # 方图、朋友圈
    "4:5": (1440, 1800),    # 小红书、Instagram
    "3:4": (1080, 1440),    # 平板/文档投屏
    "4k": (3840, 2160),     # 3840×2160，u=2，字号自动翻倍
}

ALIASES = {
    "横屏": "16:9", "landscape": "16:9", "horizontal": "16:9",
    "竖屏": "9:16", "portrait": "9:16", "vertical": "9:16", "shorts": "9:16",
    "方形": "1:1", "square": "1:1",
    "小红书": "4:5",
}

# 短边 1080 基准下的一套字号/间距（16:9 1080p 的历史取值，别单独改）
BASE = {
    "title": 108,      # 片头主标题
    "card_title": 72,  # 卡标题
    "h3": 64,          # 小标题 / 黑板四格主词
    "body": 48,        # 正文
    "sub": 40,         # 副标题
    "note": 34,        # 注释
    "label": 30,       # 标签/集号
    "min": 34,         # 可读下限
    "safe_x": 135,     # 左右安全边
    "safe_y": 120,     # 上下安全边
    "gap": 64,         # 正文行距
    "px_per_inch": 144,
}


def parse_size(text):
    """'1080x1920' / '1080X1920' / '1080*1920' -> (1080, 1920)"""
    for sep in ("x", "X", "*", "×"):
        if sep in str(text):
            a, b = str(text).split(sep, 1)
            return _even(int(a)), _even(int(b))
    raise ValueError("尺寸写成 宽x高，例如 1080x1920：%r" % text)


def _even(v):
    v = int(v)
    return v - v % 2


def resolve(canvas):
    """canvas 配置 -> (W, H)。支持 {'preset': '9:16'} 或 {'width':..,'height':..}。"""
    canvas = canvas or {}
    preset = canvas.get("preset")
    if preset:
        p = ALIASES.get(str(preset).lower().strip(), preset)
        if p not in PRESETS:
            raise KeyError("未知画布预设 %r，可选：%s" % (preset, ", ".join(PRESETS)))
        w, h = PRESETS[p]
    else:
        w, h = canvas.get("width"), canvas.get("height")
    if not w or not h:
        w, h = PRESETS["16:9"]
    return _even(w), _even(h)


def unit(w, h):
    return min(w, h) / 1080.0


def tokens(w, h):
    """当前画布的一套尺寸令牌（整数像素）。"""
    u = unit(w, h)
    t = {k: int(round(v * u)) for k, v in BASE.items() if k != "px_per_inch"}
    t["unit"] = round(u, 4)
    t["width"], t["height"] = w, h
    t["px_per_inch"] = BASE["px_per_inch"]
    return t


def slide_inches(w, h):
    """PPT 幻灯片尺寸（英寸），按 144 px = 1 in。"""
    ppi = BASE["px_per_inch"]
    return round(w / ppi, 4), round(h / ppi, 4)


def subtitle_size(w, h):
    """烧录字幕字号：按短边 4.5%，1080p 落地 49≈48，竖屏同样 48，4K 翻倍。"""
    return max(16, int(round(min(w, h) * 0.045)))


def describe(w, h):
    t = tokens(w, h)
    return "%d×%d（%s，令牌系数 %.2f，正文 %d，字幕 %d）" % (
        w, h, "横屏" if w > h else ("竖屏" if h > w else "方形"),
        t["unit"], t["body"], subtitle_size(w, h))


if __name__ == "__main__":
    for name in PRESETS:
        w, h = PRESETS[name]
        si = slide_inches(w, h)
        print("%-6s %s  PPT %.2f×%.2f in" % (name, describe(w, h), si[0], si[1]))
    if len(sys.argv) > 1:
        print("自定义:", describe(*parse_size(sys.argv[1])))
