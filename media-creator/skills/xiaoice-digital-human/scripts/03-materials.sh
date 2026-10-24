#!/usr/bin/env bash
# 拉取视觉素材枚举：花字模板 + 转场动画
# 只读，不产生费用。写代码时不要硬编码枚举值，实时拉取更稳。
set -euo pipefail

: "${XIAOICE_KEY:?请先 export XIAOICE_KEY=你的订阅密钥}"
BASE="${BASE:-https://aibeings-vip.xiaoice.com}"

echo "=== 花字模板列表 GET /openapi/video/material/artFontTemplates ==="
curl -s --max-time 30 "$BASE/openapi/video/material/artFontTemplates" \
  -H "subscription-key: $XIAOICE_KEY" -o /tmp/artfont.json

python - <<'PY'
import json
d = json.load(open('/tmp/artfont.json', encoding='utf-8'))
if d.get('code') != 200:
    print('业务失败:', d.get('code'), d.get('message')); raise SystemExit(1)
items = d.get('data') or []
print('共 %d 个，用于 displayTexts[].artFontTemplateName' % len(items))
for it in items:
    print('  %-10s %s' % (it['name'], it.get('preview', '')[:70]))
PY

echo
echo "=== 转场动画列表 GET /openapi/video/material/transferEffects ==="
curl -s --max-time 30 "$BASE/openapi/video/material/transferEffects" \
  -H "subscription-key: $XIAOICE_KEY" -o /tmp/trans.json

python - <<'PY'
import json
d = json.load(open('/tmp/trans.json', encoding='utf-8'))
if d.get('code') != 200:
    print('业务失败:', d.get('code'), d.get('message')); raise SystemExit(1)
items = d.get('data') or []
print('共 %d 个，用于 scenes[].transferEffects[].type' % len(items))
for it in items:
    print('  %-20s %-10s %s' % (it['type'], it.get('name'), it.get('previewGif', '')[:60]))
PY

echo
echo "字体枚举见官方文档 show/156（font 字段用字体序号 1-112，默认 6 = 微软雅黑）。"
