#!/usr/bin/env bash
# 完整编辑器模式：公式 + 字幕 + 文字素材 + 图片 + 背景图 + 背景音乐 + 转场
#
# ⚠️ 这个脚本会产生真实计费，请先确认账户额度。
#
# 用法:
#   ./05-generate-editor.sh <bizId> "播报文本（可含 $公式$）"
#
# 实测说明：下面这套字段组合（含 displayTexts + displayImages + backgroundImage
# + backgroundMusic + caption + transferEffects + hasLatex）已实测提交成功，
# 返回 taskId。但整体视频渲染效果尚未逐项肉眼验证，请以实际成片为准。
set -euo pipefail

BIZ_ID="${1:?用法: $0 <bizId> \"播报文本\"}"
TEXT="${2:?用法: $0 <bizId> \"播报文本\"}"
: "${XIAOICE_KEY:?请先 export XIAOICE_KEY=你的订阅密钥}"
BASE="${BASE:-https://aibeings-vip.xiaoice.com}"

CANVAS_W=1920   # 横屏示例，便于展示图文混排；竖屏改成 1080 / 1920
CANVAS_H=1080

curl -s --max-time 30 -X POST "$BASE/openapi/video/detailDigitalEmployee" \
  -H "Content-Type: application/json" -H "subscription-key: $XIAOICE_KEY" \
  -d "{\"bizId\":\"$BIZ_ID\"}" -o /tmp/detail.json

PAYLOAD=$(python - "$CANVAS_W" "$CANVAS_H" "$TEXT" <<'PY'
import json, re, sys

canvas_w, canvas_h, text = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
d = json.load(open('/tmp/detail.json', encoding='utf-8'))
if d.get('code') != 200:
    print(json.dumps({'error': 'detail 失败'})); raise SystemExit(0)
x = d['data']

vh = x.get('virtualHumanId')
postures = x.get('postureInfos') or []
voice = x.get('defaultVoiceId') or ((x.get('voiceInfos') or [{}])[0].get('voiceId'))
posture = postures[0]

# 虚拟人按预览图等比缩放到画布高度，靠左放置，右侧留给图文
base = (posture.get('previewPicture') or '').rsplit('/', 1)[-1]
m = re.search(r'_(\d+)x(\d+)\.', base)
if m:
    sw, sh = int(m.group(1)), int(m.group(2))
    scale = min(canvas_w / sw, canvas_h / sh)
    h = int(round(sh * scale))
    w = int(round(sw * scale))
    if w % 2: w += 1
    if h % 2: h += 1
else:
    w, h = canvas_h * 9 // 16, canvas_h
    if w % 2: w += 1

payload = {
    "outputVideoName": "editor-demo",
    "outputVideoFormat": "mp4",
    "width": canvas_w,
    "height": canvas_h,
    "aigcWatermark": False,
    "creationDetail": {
        # 全局背景音乐：设置后所有场景内的 backgroundMusic 都会失效
        "backgroundMusic": {
            "mediaUrl": "https://virtualman.oss-cn-beijing.aliyuncs.com/media_prefabricate/3c03c1b2-79a9-490a-991f-7cb6be8e48ae.mp3",
            "volume": 0.2,
            "speed": 1,
            "loop": True,
        },
        "scenes": [{
            # --- LaTeX：含公式时建议显式开启 ---
            "hasLatex": True,

            # --- 转场动画（type 取自 material/transferEffects）---
            "transferEffects": [{"type": "wipe_left", "duration": 1}],

            # --- 字幕：zIndex 必填；topLeft/topCenter/topRight 全 false 则居中 ---
            "caption": {
                "topCenter": True,
                "zIndex": 60,
                "attributes": {
                    "fontSize": 40,
                    "fontColor": "#ffffff",
                    "bold": True,
                },
            },

            # --- 文字素材：attributes 必填；zIndex 同场景内不能重复 ---
            "displayTexts": [{
                "content": "开场大字",
                "artFontTemplateName": "MHM_1",       # 取自 material/artFontTemplates
                "zIndex": 30,
                "attributes": {
                    "x": 100, "y": 200,
                    "fontSize": 80,
                    "font": 6,                          # 字体序号，6 = 微软雅黑（默认）
                    "fontColor": "#FFDE00",
                    "bold": True,
                },
                "effectIn":  {"type": "slide_left_in",  "duration": 1},
                "effectOut": {"type": "slide_right_out", "duration": 1},
            }],

            # --- 图片素材：mediaUrl ≤10MB，attributes 四字段全必填 ---
            "displayImages": [{
                "mediaUrl": "https://virtualman.oss-cn-beijing.aliyuncs.com/media_upload/3e080112-7f16-45d0-9648-d0f8bb729d6c.png",
                "zIndex": 10,
                "attributes": {"x": 1400, "y": 100, "width": 400, "height": 400},
            }],

            # --- 场景背景图：自动拉伸覆盖全屏，固定占 zIndex 1 ---
            "backgroundImage": {
                "mediaUrl": "https://virtualman.oss-cn-beijing.aliyuncs.com/media_prefabricate/db4f5a4a-81e7-4ca3-9cf6-d4c31f6a2069.png"
            },

            # --- TTS：rate/pitch 限 0.6-1.5，volume 限 0-100；latexStyle 只作用于公式 ---
            "tts": {
                "voiceId": voice,
                "rate": 1, "pitch": 1, "volume": 50,
                "latexStyle": {
                    "fontSize": 48,
                    "fontColor": "#FFDE00",
                    "backgroundColor": "#00000080",
                    "radius": 8,
                    "strokeOn": True,
                    "strokeColor": "#000000",
                    "strokeWidth": 4.8,
                },
            },

            # --- 虚拟人：宽高必须与预览图等比，否则会被拉伸变形 ---
            "virtualHuman": {
                "virtualHumanId": vh,
                "virtualHumanPostureId": posture['bizId'],
                "zIndex": 20,
                "attributes": {"width": w, "height": h, "x": 0, "y": 0},
            },

            # --- 播报文本：JSON 里 LaTeX 反斜杠要双写 ---
            "voiceTexts": [text],
        }],
    },
}
print(json.dumps(payload, ensure_ascii=False))
PY
)

if echo "$PAYLOAD" | grep -q '"error"'; then
  echo "准备失败"; echo "$PAYLOAD"; exit 1
fi

echo "=== 提交请求体（含全部编辑器字段）==="
echo "$PAYLOAD" | python -m json.tool --no-ensure-ascii

echo
echo "=== 提交任务 ==="
echo "$PAYLOAD" | curl -s --max-time 40 -X POST "$BASE/openapi/video/task/v2/submit" \
  -H "Content-Type: application/json" -H "subscription-key: $XIAOICE_KEY" \
  --data-binary @- | tee /tmp/submit.json

echo
python - <<'PY'
import json
d = json.load(open('/tmp/submit.json', encoding='utf-8'))
if d.get('code') != 200:
    print('业务失败:', d.get('code'), d.get('message')); raise SystemExit(1)
data = d['data']
tid = data.get('id') if isinstance(data, dict) else data
print('taskId =', tid)
open('/tmp/taskid.txt', 'w').write(tid or '')
PY

echo
echo "另外两个没进本示例的可选字段（需要时自行加）："
echo "  scenes[].voiceUrl        —— 用现成音频驱动，音频时长决定场景时长；会令自动字幕失效"
echo "  scenes[].displayVideos   —— 叠加视频，MP4 ≤300MB；不会自动截断，按顺序播完"
echo "  scenes[].backgroundMusic —— 场景音乐，存在全局背景音乐时失效"
