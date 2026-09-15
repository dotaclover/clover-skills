#!/usr/bin/env bash
# 从任务列表移除任务。
#
# ⚠️⚠️ 这不是「取消任务」！实测结论：
#   - remove 后任务立刻从 pageQuery 列表消失
#   - 但 detail 查该 taskId 仍然是 running，后台继续生成、继续计费
#   - 小冰没有暴露真正的取消接口
#   仅用于清理列表 / 隐藏测试任务。无法止损。
#
# 用法: ./08-remove-tasks.sh <taskId> [taskId2] [...]
set -euo pipefail

[ $# -ge 1 ] || { echo "用法: $0 <taskId> [taskId2] [...]"; exit 1; }
: "${XIAOICE_KEY:?请先 export XIAOICE_KEY=你的订阅密钥}"
BASE="${BASE:-https://aibeings-vip.xiaoice.com}"

IDS=$(python -c "
import json, sys
print(json.dumps({'taskIds': sys.argv[1:]}))
" "$@")

echo "请求体: $IDS"
echo "=== 调用 remove ==="
curl -s --max-time 30 -X POST "$BASE/openapi/video/task/v2/remove" \
  -H "Content-Type: application/json" -H "subscription-key: $XIAOICE_KEY" \
  -d "$IDS" | tee /tmp/remove.json

echo
echo "=== 验证：删除后再查第一个任务（预期仍是 running）==="
FIRST="$1"
curl -s --max-time 30 "$BASE/openapi/video/task/v2/detail?taskId=$FIRST" \
  -H "subscription-key: $XIAOICE_KEY" | python -c "
import json, sys
d = json.load(sys.stdin)
x = d.get('data')
if isinstance(x, list): x = x[0] if x else {}
if isinstance(x, dict):
    print('code=%s status=%s error=%s' % (d.get('code'), x.get('status'), x.get('error')))
    if x.get('status') == 'running':
        print()
        print('⚠️ 确认：任务从列表移除了，但仍在运行、仍在计费。remove 不是取消。')
else:
    print('code=%s message=%s' % (d.get('code'), d.get('message')))
"
