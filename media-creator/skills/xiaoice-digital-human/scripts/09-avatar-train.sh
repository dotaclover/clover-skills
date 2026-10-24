#!/usr/bin/env bash
# 形象训练全流程：commit → 质检轮询 → 启动训练 → 训练结果
#
# ⚠️ 会产生真实计费（训练成本远高于单条视频，且耗时可达数十分钟到数小时）。
#
# ⚠️ 两个素材 URL 必须公网可访问、且能被小冰服务器主动拉取到。
#
# 用法:
#   ./09-avatar-train.sh <训练视频URL> <授权视频URL> <形象名称> [voiceBizId]
#
# 注意：质检通过不会自动开始训练，必须显式调 start-training —— 这是最容易漏的一步。
set -euo pipefail

TRAIN_URL="${1:?用法: $0 <训练视频URL> <授权视频URL> <形象名称> [voiceBizId]}"
AUTH_URL="${2:?缺少授权视频URL}"
NAME="${3:?缺少形象名称}"
VOICE_BIZ_ID="${4:-}"
: "${XIAOICE_KEY:?请先 export XIAOICE_KEY=你的订阅密钥}"
BASE="${BASE:-https://aibeings-vip.xiaoice.com}"

echo "=== 1. 提交训练 GET commit ==="
curl -s --max-time 40 -X POST "$BASE/openapi/customize/zero/commit" \
  -H "Content-Type: application/json" -H "subscription-key: $XIAOICE_KEY" \
  -d "{\"vhModelType\":\"STUDIO\",\"trainingVideoUrl\":\"$TRAIN_URL\",\"authVideoUrl\":\"$AUTH_URL\",\"voiceTemplateVersion\":1}" \
  | tee /tmp/commit.json

BIZ_ID=$(python -c "
import json
d = json.load(open('/tmp/commit.json', encoding='utf-8'))
if d.get('code') != 200:
    print('', end=''); raise SystemExit(1)
x = d['data']
print(x.get('id') if isinstance(x, dict) else (x or ''))
")
[ -n "$BIZ_ID" ] || { echo "未拿到 bizId"; exit 1; }
echo "bizId = $BIZ_ID"
echo "$BIZ_ID" > /tmp/bizid.txt

echo
echo "=== 2. 质检轮询 GET get-ckq-result ==="
echo "（status: 0 进行中 / 1 质检通过 / -1 失败）"
for i in $(seq 1 120); do
  curl -s --max-time 30 "$BASE/openapi/customize/zero/get-ckq-result?bizId=$BIZ_ID" \
    -H "subscription-key: $XIAOICE_KEY" -o /tmp/ckq.json
  read -r STATUS PROGRESS MSG <<< "$(python -c "
import json
d = json.load(open('/tmp/ckq.json', encoding='utf-8'))
x = d.get('data') or {}
print('%s %s %s' % (x.get('status'), x.get('progress') or 0, (x.get('message') or '').replace(' ', '_')))
")"
  echo "[$i] status=$STATUS progress=$PROGRESS $MSG"

  if [ "$STATUS" = "1" ]; then echo "质检通过"; break; fi
  if [ "$STATUS" = "-1" ]; then echo "质检失败: $MSG"; exit 1; fi
  sleep 15
done

[ "$STATUS" = "1" ] || { echo "质检超时"; exit 1; }

echo
echo "=== 3. 启动训练（质检通过不会自动开始，必须显式调用）==="
if [ -n "$VOICE_BIZ_ID" ]; then
  START_BODY="{\"bizId\":\"$BIZ_ID\",\"name\":\"$NAME\",\"voiceBizId\":\"$VOICE_BIZ_ID\"}"
  echo "绑定声音 voiceBizId=$VOICE_BIZ_ID（注意：是 voiceBizId，不是 bizId）"
else
  START_BODY="{\"bizId\":\"$BIZ_ID\",\"name\":\"$NAME\"}"
fi
echo "请求体: $START_BODY"
curl -s --max-time 40 -X POST "$BASE/openapi/customize/zero/start-training" \
  -H "Content-Type: application/json" -H "subscription-key: $XIAOICE_KEY" \
  -d "$START_BODY" | tee /tmp/start.json

echo
echo "=== 4. 训练结果轮询 POST get-training-result ==="
echo "（status: 1 成功 / -1 失败；成功后返回新形象 bizId）"
for i in $(seq 1 480); do
  curl -s --max-time 30 -X POST "$BASE/openapi/customize/zero/get-training-result" \
    -H "Content-Type: application/json" -H "subscription-key: $XIAOICE_KEY" \
    -d "{\"bizId\":\"$BIZ_ID\"}" -o /tmp/train.json
  read -r STATUS PROGRESS NEW_ID MSG <<< "$(python -c "
import json
d = json.load(open('/tmp/train.json', encoding='utf-8'))
x = d.get('data') or {}
print('%s %s %s %s' % (x.get('status'), x.get('progress') or 0,
      x.get('bizId') or '', (x.get('message') or '').replace(' ', '_')))
")"
  echo "[$i] status=$STATUS progress=$PROGRESS 新形象=$NEW_ID $MSG"

  if [ "$STATUS" = "1" ] && [ -n "$NEW_ID" ]; then
    echo
    echo "训练成功！新形象 bizId = $NEW_ID"
    echo "提示：新形象需重新走 detailDigitalEmployee 取 virtualHumanId / 姿态 / 声音。"
    exit 0
  fi
  if [ "$STATUS" = "-1" ]; then echo "训练失败: $MSG"; exit 1; fi
  sleep 30
done

echo "训练轮询超时（4 小时），任务可能仍在进行，可稍后手动再查。"
exit 1
