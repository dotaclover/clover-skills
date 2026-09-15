#!/usr/bin/env bash
# 拉取公共形象列表（数字员工，categoryList=[0]，modelType=STUDIO）
# 只读，不产生费用
set -euo pipefail

: "${XIAOICE_KEY:?请先 export XIAOICE_KEY=你的订阅密钥}"
BASE="${BASE:-https://aibeings-vip.xiaoice.com}"

# 分页拉全量：pageSize 最大 100
for PAGE in 1 2 3; do
  echo "=== 第 $PAGE 页 ==="
  curl -s --max-time 30 -X POST "$BASE/openapi/video/queryDigitalEmployee" \
    -H "Content-Type: application/json" \
    -H "subscription-key: $XIAOICE_KEY" \
    -d "{\"categoryList\":[0],\"modelType\":\"STUDIO\",\"pageIndex\":$PAGE,\"pageSize\":100}" \
    -o "avatars_page${PAGE}.json"

  python -c "
import json, sys
d = json.load(open('avatars_page${PAGE}.json', encoding='utf-8'))
if d.get('code') != 200:
    print('业务失败:', d.get('code'), d.get('message')); raise SystemExit(1)
data = d['data']
print('total=%s pages=%s 本页=%d' % (data.get('total'), data.get('pages'), len(data.get('records') or [])))
for r in (data.get('records') or [])[:5]:
    print('  %-18s %-10s %s' % (r['bizId'], r['name'].strip(), r.get('language', '')))
"
done

echo
echo "提示：用 02-avatar-detail.sh <bizId> 查某个形象的 virtualHumanId / 姿态 / 声音。"
echo "注意：姿态图尺寸各形象不同，提交前必须按预览图算宽高比。"
