#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""双人对谈视频：一个形象演两个角色，左上/右下轮流说话。

⚠️ 这个脚本会产生真实计费（每句语音都算时长）。

实测确认的关键规则：
  - 一个 scene 只能有一个 virtualHuman（传数组会 407）
  - 每个场景用「自己那方的固定坐标」，实现两人各占一角、位置不动只换人
  - displayTexts 数组里多个元素的 zIndex 必须互不相同，否则 420 图层序号错误
  - scene.backgroundImage 的实际层级不受 zIndex 控制，会盖在虚拟人之上（是前景不是背景）
  - 背景图的 mediaUrl 只有小冰 CDN（virtualman.oss-cn-beijing.aliyuncs.com）会被接受，
    外部图床一律 410 媒体资源url错误
  - 公共音色 101-wenyou（男）所有形象可用；账号内音色多支持 zh-CN/zh-HK/en-US 三语

用法:
    export XIAOICE_KEY=你的订阅密钥
    python 11-dialogue-video.py <bizId> [--bg https://virtualman.oss-cn-beijing.aliyuncs.com/...]

先跑 02-avatar-detail.sh 拿到 bizId 与 postureInfos 的两个姿态 bizId，
填到下面的 POS_A / POS_B。
"""
import argparse
import json
import os
import subprocess
import sys

BASE = os.environ.get("BASE", "https://aibeings-vip.xiaoice.com")
KEY = os.environ.get("XIAOICE_KEY") or sys.exit("请先 export XIAOICE_KEY=你的订阅密钥")

# ---- 画布与角色布局（竖屏 1080x1920）----
CANVAS_W, CANVAS_H = 1080, 1920
BOX_W, BOX_H = 430, 764          # 与姿态图 720x1271 等比
BOX_A = (55, 470)                # 角色 A：左上
BOX_B = (595, 990)               # 角色 B：右下
NAME_A, NAME_B = "Tom", "Jerry"
C_A, C_B = "#FFE400", "#4DD0FF"  # A 黄、B 蓝
C_DIM = "#8C97A6"                # 非说话方压暗

VOICE = "101-wenyou"             # 公共男声

# ---- 台词（说话人, 内容）----
DIALOG = [
    ("A", "Hey Jerry, how's your day going?"),
    ("B", "It's okay. Work has been pretty easy lately."),
    ("A", "Haha, sounds nice. Are you enjoying the slower pace?"),
    ("B", "Not really. I don't like working long hours."),
]


def name_tag(text, box, color, z):
    return {
        "content": text,
        "zIndex": z,
        "attributes": {
            "x": box[0] + 20, "y": box[1] - 96,
            "font": 6, "fontSize": 56,
            "fontColor": color, "bold": True,
            "strokeOn": True, "strokeColor": "#000000", "strokeWidth": 6,
        },
    }


def build(vid, pos_a, pos_b, bg):
    roles = {
        "A": {"posture": pos_a, "box": BOX_A},
        "B": {"posture": pos_b, "box": BOX_B},
    }
    scenes = []
    for who, text in DIALOG:
        r = roles[who]
        x, y = r["box"]
        scene = {
            "virtualHuman": {
                "virtualHumanId": vid,
                "virtualHumanPostureId": r["posture"],
                "zIndex": 20,
                "attributes": {"x": x, "y": y, "width": BOX_W, "height": BOX_H},
            },
            "tts": {"voiceId": VOICE, "rate": 1, "pitch": 1, "volume": 50},
            "voiceTexts": [text],
            "caption": {
                "topLeft": True,
                "zIndex": 60,
                "attributes": {
                    "x": 120, "y": 1780, "font": 6, "fontSize": 52,
                    "fontColor": "#FFFFFF", "bold": True,
                    "strokeOn": True, "strokeColor": "#000000", "strokeWidth": 5,
                },
            },
            # 两个名牌常驻，说话方高亮。zIndex 必须互不相同。
            "displayTexts": [
                name_tag(NAME_A, BOX_A, C_A if who == "A" else C_DIM, 30),
                name_tag(NAME_B, BOX_B, C_B if who == "B" else C_DIM, 31),
            ],
        }
        if bg:
            scene["backgroundImage"] = {"mediaUrl": bg, "zIndex": 1}
        scenes.append(scene)

    return {
        "outputVideoName": "dialogue-video",
        "outputVideoFormat": "mp4",
        "width": CANVAS_W,
        "height": CANVAS_H,
        "aigcWatermark": False,
        "creationDetail": {"scenes": scenes},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("biz_id", help="形象 bizId（来自 01/02 脚本）")
    ap.add_argument("--pos-a", required=True, help="角色 A 的姿态 bizId")
    ap.add_argument("--pos-b", required=True, help="角色 B 的姿态 bizId")
    ap.add_argument("--vid", required=True, help="virtualHumanId（来自 02 脚本）")
    ap.add_argument("--bg", default="", help="背景图 mediaUrl（必须是小冰 CDN 域名）")
    args = ap.parse_args()

    payload = build(args.vid, args.pos_a, args.pos_b, args.bg)
    print(f"场景数 {len(payload['creationDetail']['scenes'])}"
          f" | 背景 {'有' if args.bg else '无（白底）'}")
    print("⚠️ 本操作产生真实计费")

    r = subprocess.run(
        ["curl", "-s", "--noproxy", "*", "--max-time", "40", "-X", "POST",
         f"{BASE}/openapi/video/task/v2/submit",
         "-H", "Content-Type: application/json",
         "-H", f"subscription-key: {KEY}",
         "--data-binary", "@-"],
        input=json.dumps(payload, ensure_ascii=False).encode(), capture_output=True)
    d = json.loads(r.stdout.decode())
    if d.get("code") != 200:
        sys.exit(f"提交失败: {d.get('code')} {d.get('message')}")
    tid = d["data"]["id"] if isinstance(d["data"], dict) else d["data"]
    print("taskId =", tid)
    print("用 06-poll-task.sh 轮询下载")


if __name__ == "__main__":
    main()
