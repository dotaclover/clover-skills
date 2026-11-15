# -*- coding: utf-8 -*-
"""三集统一封面，1080x1440（抖音竖版封面 3:4）。"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent.parent / "output" / "covers"
OUT.mkdir(parents=True, exist_ok=True)

W, H = 1080, 1440
C_TOP, C_BOT = (8, 11, 16), (15, 21, 29)
C_ACCENT = (18, 227, 155)
C_TEXT = (243, 246, 250)
C_DIM = (138, 152, 168)
C_LINE = (34, 45, 58)

F_BOLD = r"C:\Windows\Fonts\msyhbd.ttc"
F_REG = r"C:\Windows\Fonts\msyh.ttc"

SERIES = "顺哥TRAE教程系列"
KIND = "小程序开发"

EPS = [
    dict(n="01", line1="一句话", line2="到可演示原型",
         sub="提需求·出PRO·定MVP·出原型",
         tag="四步走完，只做到原型"),
    dict(n="02", line1="界面", line2="改了三遍",
         sub="砍字段·拆职责·换话术",
         tag="界面改三遍，代码只写一遍"),
    dict(n="03", line1="代码", line2="只写一遍",
         sub="三页·一个key·直接上真机",
         tag="能用了，发MVP，代码开源"),
]


def bg():
    im = Image.new("RGB", (W, H), C_TOP)
    d = ImageDraw.Draw(im)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)],
               fill=tuple(int(C_TOP[i] + (C_BOT[i] - C_TOP[i]) * t) for i in range(3)))
    return im


def cover(ep, i):
    im = bg()
    d = ImageDraw.Draw(im)

    f_s = ImageFont.truetype(F_REG, 30)
    d.ellipse([80, 86, 94, 100], fill=C_ACCENT)
    d.text((110, 76), SERIES, font=f_s, fill=C_DIM)
    w = d.textbbox((0, 0), KIND, font=f_s)[2]
    d.text((W - 80 - w, 76), KIND, font=f_s, fill=C_DIM)

    f_n = ImageFont.truetype(F_BOLD, 150)
    d.text((72, 170), ep["n"], font=f_n, fill=C_ACCENT)
    d.rectangle([80, 350, 80 + 120, 356], fill=C_ACCENT)

    f_t = ImageFont.truetype(F_BOLD, 112)
    d.text((76, 420), ep["line1"], font=f_t, fill=C_TEXT)
    d.text((76, 556), ep["line2"], font=f_t, fill=C_TEXT)

    f_sub = ImageFont.truetype(F_BOLD, 44)
    d.text((80, 740), ep["sub"], font=f_sub, fill=C_DIM)

    # 右侧集数导轨，突出这一集的序号
    d.line([(938, 424), (938, 700)], fill=C_LINE, width=2)
    f_i = ImageFont.truetype(F_BOLD, 46)
    for k, num in enumerate(["01", "02", "03"]):
        cur = num == ep["n"]
        d.text((968, 430 + k * 108), num, font=f_i,
               fill=C_ACCENT if cur else (58, 70, 86))
        if cur:
            d.rectangle([946, 438 + k * 108, 954, 480 + k * 108], fill=C_ACCENT)

    d.line([(80, 1180), (W - 80, 1180)], fill=C_LINE, width=2)
    f_tag = ImageFont.truetype(F_REG, 38)
    d.text((80, 1226), ep["tag"], font=f_tag, fill=C_TEXT)
    f_no = ImageFont.truetype(F_REG, 32)
    no = f"第 {i + 1} 集 · 共 3 集"
    d.text((80, 1330), no, font=f_no, fill=C_DIM)
    repo = "gitee.com/clover/trae-decision-recorder" if ep["n"] == "03" else "全程录屏"
    w2 = d.textbbox((0, 0), repo, font=f_no)[2]
    d.text((W - 80 - w2, 1330), repo, font=f_no,
           fill=C_ACCENT if ep["n"] == "03" else C_DIM)

    p = OUT / f"ep{ep['n']}.png"
    im.save(p)
    return p


for i, ep in enumerate(EPS):
    print(cover(ep, i))
