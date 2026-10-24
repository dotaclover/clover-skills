#!/usr/bin/env bash
# 声音训练全流程：commit → get-training-result
#
# ⚠️ 会产生真实计费。
# ⚠️ 音频 URL 必须公网可访问、且能被小冰服务器拉取到。
#
# 用法:
#   ./10-voice-train.sh <音频URL> <声音名称> [languageType] [音频对应文本]
#
# languageType: 单语传语言代码（如 ZH / EN），多语传 MULTI（MULTI 时可加 refineNoise）
set -euo pipefail

AUDIO_URL="${1:?用法: $0 <音频URL> <声音名称> [languageType] [音频对应文本]}"
NAME="${2:?缺少声音名称}"
LANG="${3:-ZH}"
TEXT="${4:-}"
: "${XIAOICE_KEY:?请先 export XIAOICE_KEY=你的订阅密钥}"
BASE="${BASE:-https://aibeings-vip.xiaoice.com}"

BODY=$(python -c "
import json, sys
audio, name, lang, text = sys.argv[1:5]
p = {'name': name, 'trainingAudioUrl': audio, 'languageType': lang}
if text:
    p['audioText'] = text
if lang == 'MULTI':
    p['reduceNoise'] = 1
print(json.dumps(p, ensure_ascii=False))
" "$AUDIO_URL" "$NAME" "$LANG" "$TEXT")

echo "=== 1. 提交声音训练 POST voice/commit ==="
echo "请求体: $BODY"
curl -s --max-time 40 -X POST "$BASE/openapi/customize/zero/voice/commit" \
  -H "Content-Type: application/json" -H "subscription-key: $XIAOICE_KEY" \
  -d "$BODY" | tee /tmp/vcommit.json

BIZ_ID=$(python -c "
import json
d = json.load(open('/tmp/vcommit.json', encoding='utf-8'))
if d.get('code') != 200: raise SystemExit(1)
x = d['data']
print(x.get('id') if isinstance(x, dict) else (x or ''))
")
[ -n "$BIZ_ID" ] || { echo "未拿到 bizId"; exit 1; }
echo "bizId = $BIZ_ID"

echo
echo "=== 2. 轮询训练结果 POST voice/get-training-result ==="
for i in $(seq 1 240); do
  curl -s --max-time 30 -X POST "$BASE/openapi/customize/zero/voice/get-training-result" \
    -H "Content-Type: application/json" -H "subscription-key: $XIAOICE_KEY" \
    -d "{\"bizId\":\"$BIZ_ID\"}" -o /tmp/vres.json

  python -c "
import json
d = json.load(open('/tmp/vres.json', encoding='utf-8'))
x = d.get('data') or {}
print(json.dumps(x, ensure_ascii=False)[:300])
"

  DONE=$(python -c "
import json
d = json.load(open('/tmp/vres.json', encoding='utf-8'))
x = d.get('data') or {}
print(x.get('status'))
")
  if [ "$DONE" = "1" ]; then
    echo
    echo "声音训练成功！"
    python -c "
import json
d = json.load(open('/tmp/vres.json', encoding='utf-8'))
x = d['data']
print('  voiceBizId     =', x.get('voiceBizId'), '  <- 绑定形象训练时用这个')
print('  voiceOpenapiId =', x.get('voiceOpenapiId'), '  <- 生成视频时 tts.voiceId 用这个')
print()
print('  ⚠️ 两者不要混用：绑定形象用 voiceBizId，生成视频用 voiceOpenapiId。')
print('  ⚠️ 注意字段名是 voiceOpenapiId（小写 api），不是 voiceOpenApiId。')
"
    exit 0
  fi
  if [ "$DONE" = "-1" ]; then
    python -c "
import json
d = json.load(open('/tmp/vres.json', encoding='utf-8'))
print('训练失败:', (d.get('data') or {}).get('message'))
"
    exit 1
  fi
  echo "[$i] 训练中"
  sleep 20
done

echo "轮询超时，任务可能仍在进行。"
exit 1
