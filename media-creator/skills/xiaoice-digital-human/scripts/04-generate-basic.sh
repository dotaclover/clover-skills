#!/usr/bin/env bash
# 最简播报视频：虚拟人 + TTS + 文本
#
# ⚠️ 这个脚本会产生真实计费，请先确认账户额度。
#
# 用法:
#   ./04-generate-basic.sh <bizId> "要播报的文本"
#
# 完整的参数说明见 ../SKILL.md 的「编辑器模式：完整功能清单」。
set -euo pipefail

BIZ_ID="${1:?用法: $0 <bizId> \"要播报的文本\"}"
TEXT="${2:?用法: $0 <bizId> \"要播报的文本\"}"
: "${XIAOICE_KEY:?请先 export XIAOICE_KEY=你的订阅密钥}"
BASE="${BASE:-https://aibeings-vip.xiaoice.com}"

CANVAS_W=1080
CANVAS_H=1920

# ---- 第一步：取详情（virtualHumanId / 姿态 / 声音），并按预览图算好宽高比 ----
curl -s --max-time 30 -X POST "$BASE/openapi/video/detailDigitalEmployee" \
  -H "Content-Type: application/json" -H "subscription-key: $XIAOICE_KEY" \
  -d "{\"bizId\":\"$BIZ_ID\"}" -o /tmp/detail.json

PAYLOAD=$(python - "$CANVAS_W" "$CANVAS_H" "$TEXT" <<'PY'
import json, re, sys

canvas_w, canvas_h, text = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]

d = json.load(open('/tmp/detail.json', encoding='utf-8'))
if d.get('code') != 200:
    print(json.dumps({'error': 'detail 失败: %s' % d.get('message')})); raise SystemExit(0)
x = d['data']

vh = x.get('virtualHumanId')
postures = x.get('postureInfos') or []
voice = x.get('defaultVoiceId') or ((x.get('voiceInfos') or [{}])[0].get('voiceId'))
if not vh or not postures or not voice:
    print(json.dumps({'error': '该形象缺少 virtualHumanId / 姿态 / 声音'})); raise SystemExit(0)

posture = postures[0]
# 从姿态预览图 URL 解析原始宽高，形如 ..._2160x3840.webp
base = (posture.get('previewPicture') or '').rsplit('/', 1)[-1]
m = re.search(r'_(\d+)x(\d+)\.', base)

if m:
    sw, sh = int(m.group(1)), int(m.group(2))
    scale = min(canvas_w / sw, canvas_h / sh)
    w = int(round(sw * scale)); h = int(round(sh * scale))
    if w % 2: w += 1
    if h % 2: h += 1
    ax, ay = (canvas_w - w) // 2, (canvas_h - h) // 2
else:
    # 拿不到尺寸就退回铺满画布（对 9:16 姿态图是正确的）
    w, h, ax, ay = canvas_w, canvas_h, 0, 0

payload = {
    "outputVideoName": "basic-demo",
    "outputVideoFormat": "mp4",
    "width": canvas_w,
    "height": canvas_h,
    "aigcWatermark": False,
    "creationDetail": {
        "scenes": [{
            "virtualHuman": {
                "virtualHumanId": vh,
                "virtualHumanPostureId": posture['bizId'],
                "zIndex": 20,
                "attributes": {"width": w, "height": h, "x": ax, "y": ay},
            },
            "tts": {"voiceId": voice, "rate": 1, "pitch": 1, "volume": 50},
            "voiceTexts": [text],
        }]
    },
}
print(json.dumps(payload, ensure_ascii=False))
PY
)

if echo "$PAYLOAD" | grep -q '"error"'; then
  echo "准备失败: $(echo "$PAYLOAD" | python -c 'import json,sys; print(json.load(sys.stdin)["error"])')"
  exit 1
fi

echo "=== 提交请求体 ==="
echo "$PAYLOAD" | python -m json.tool --no-ensure-ascii

# ---- 第二步：提交 ----
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
# 兼容两种返回形态：裸字符串 或 {"id": "..."}
tid = data.get('id') if isinstance(data, dict) else data
if not tid:
    print('未拿到任务 ID'); raise SystemExit(1)
print('taskId =', tid)
open('/tmp/taskid.txt', 'w').write(tid)
print()
print('下一步：./06-poll-task.sh    （轮询并下载成片，成片链接仅 24 小时有效）')
PY
