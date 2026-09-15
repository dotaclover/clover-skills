#!/usr/bin/env bash
# 轮询任务直到完成，并立即下载成片。
#
# ⚠️ 成片 URL 仅 24 小时有效（2.5 系列还有下载次数上限），务必落盘。
#
# 用法:
#   ./06-poll-task.sh [taskId] [输出文件]
#   不带 taskId 时读取 /tmp/taskid.txt（04/05 脚本会写入）
set -euo pipefail

TASK_ID="${1:-$(cat /tmp/taskid.txt 2>/dev/null || true)}"
: "${TASK_ID:?请给 taskId：$0 <taskId> [out.mp4]}"
OUT="${2:-./${TASK_ID}.mp4}"
: "${XIAOICE_KEY:?请先 export XIAOICE_KEY=你的订阅密钥}"
BASE="${BASE:-https://aibeings-vip.xiaoice.com}"

echo "轮询任务: $TASK_ID"

for i in $(seq 1 240); do
  curl -s --max-time 30 "$BASE/openapi/video/task/v2/detail?taskId=$TASK_ID" \
    -H "subscription-key: $XIAOICE_KEY" -o /tmp/detail_poll.json

  RESULT=$(python - <<'PY'
import json, os
try:
    d = json.load(open('/tmp/detail_poll.json', encoding='utf-8'))
except Exception:
    print('PARSE_ERROR|||'); raise SystemExit(0)

if d.get('code') != 200:
    print('BIZ_ERROR|||%s' % d.get('message')); raise SystemExit(0)

x = d.get('data')
# 兼容 data 为对象（实测）或数组（文档标注）两种形态
if isinstance(x, list):
    x = x[0] if x else {}
if not isinstance(x, dict):
    print('EMPTY|||'); raise SystemExit(0)

print('%s|||%s|||%s|||%s|||%s' % (
    x.get('status'), x.get('progress'), x.get('videoUrl') or '',
    x.get('videoDurationMilliseconds') or '', x.get('error') or ''))
PY
)

  IFS='|||' read -r STATUS PROGRESS URL DURATION ERR <<< "$RESULT"

  case "$STATUS" in
    PARSE_ERROR) echo "[$i] 响应解析失败，重试中"; sleep 10; continue ;;
    BIZ_ERROR)   echo "业务失败: $ERR"; exit 1 ;;
    EMPTY)       echo "[$i] 无数据，重试中"; sleep 10; continue ;;
  esac

  # 官方枚举：running / finished / error；历史版本出现过 queued/processing/failed
  if [ "$STATUS" = "finished" ]; then
    echo "[$i] 完成。时长 ${DURATION}ms"
    if [ -z "$URL" ]; then
      echo "但未返回 videoUrl，稍后重试"; sleep 10; continue
    fi
    echo "下载成片 -> $OUT"
    curl -s --max-time 600 -o "$OUT" "$URL"
    echo "已保存: $(ls -lh "$OUT" | awk '{print $5}')"
    echo
    echo "提示：如需字幕时间轴，同一接口的 data.subtitleSentences 里有 beginTime/endTime/text。"
    exit 0
  fi

  if [ "$STATUS" = "error" ] || [ "$STATUS" = "failed" ] || [ "$STATUS" = "fail" ]; then
    echo "任务失败: $ERR"
    exit 1
  fi

  echo "[$i] $STATUS 进度=${PROGRESS:-?}"
  sleep 10
done

echo "超时未完成（轮询 40 分钟），任务可能仍在生成，可稍后手动再查。"
exit 1
