#!/usr/bin/env bash
# 列出企业下全部任务的时长汇总 —— 对账上游真实用量的唯一可靠途径。
# 只读，不产生费用。
#
# 用法: ./07-list-tasks.sh [pageSize] [userId|userEmail|userPhone]
set -euo pipefail

PAGE_SIZE="${1:-100}"
FILTER="${2:-}"
: "${XIAOICE_KEY:?请先 export XIAOICE_KEY=你的订阅密钥}"
BASE="${BASE:-https://aibeings-vip.xiaoice.com}"

BODY="{\"pageIndex\":1,\"pageSize\":$PAGE_SIZE"
if [ -n "$FILTER" ]; then
  BODY="$BODY,\"userId\":\"$FILTER\""
fi
BODY="$BODY}"

echo "请求体: $BODY"
curl -s --max-time 40 -X POST "$BASE/openapi/video/task/v2/pageQuery" \
  -H "Content-Type: application/json" -H "subscription-key: $XIAOICE_KEY" \
  -d "$BODY" -o /tmp/page.json

python - <<'PY'
import json
d = json.load(open('/tmp/page.json', encoding='utf-8'))
if d.get('code') != 200:
    print('业务失败:', d.get('code'), d.get('message')); raise SystemExit(1)

p = d.get('data') or {}
recs = p.get('records') or []
print('total=%s pages=%s 本页=%d' % (p.get('total'), p.get('pages'), len(recs)))
print()

total_ms = 0
status_count = {}
for r in recs:
    try:
        ms = float(r.get('videoDurationMilliseconds') or 0)
    except (TypeError, ValueError):
        ms = 0
    total_ms += ms
    st = r.get('status') or '?'
    status_count[st] = status_count.get(st, 0) + 1

print('%-34s %-9s %-9s %-8s %s' % ('taskId', 'status', '时长(秒)', '大小(MB)', '名称'))
for r in recs:
    try:
        sec = float(r.get('videoDurationMilliseconds') or 0) / 1000
    except (TypeError, ValueError):
        sec = 0
    size = r.get('videoSizeBytes') or 0
    print('%-34s %-9s %-9.2f %-8.2f %s' % (
        r.get('id', '')[:34], r.get('status', ''), sec,
        (size / 1024 / 1024) if isinstance(size, (int, float)) else 0,
        r.get('videoName', '')[:28]))

print()
print('状态分布:', status_count)
print('合计时长: %.2f 秒 (%.2f 分钟)' % (total_ms / 1000, total_ms / 60000))
print()
print('对照检查：把这个合计秒数 × 你的单价，与实际扣费核对；')
print('若调用方（如自建工作台）自己记账，这里的结果就是权威基准。')
print()
print('注意：已被 remove 的任务不会出现在本列表中，但可能仍在计费 ——')
print('      如怀疑有「幽灵任务」，需按已知 taskId 逐个走 detail 接口确认。')
PY
