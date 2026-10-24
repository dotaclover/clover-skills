#!/usr/bin/env bash
# 查询数字员工详情：拿 virtualHumanId、姿态列表、声音列表
# 用法: ./02-avatar-detail.sh <bizId> [baseUrl]
# 只读，不产生费用。这是提交视频前必做的一步。
set -euo pipefail

BIZ_ID="${1:?用法: $0 <bizId>}"
: "${XIAOICE_KEY:?请先 export XIAOICE_KEY=你的订阅密钥}"
BASE="${2:-${BASE:-https://aibeings-vip.xiaoice.com}}"

curl -s --max-time 30 -X POST "$BASE/openapi/video/detailDigitalEmployee" \
  -H "Content-Type: application/json" \
  -H "subscription-key: $XIAOICE_KEY" \
  -d "{\"bizId\":\"$BIZ_ID\"}" \
  -o /tmp/xiaoice_detail.json

python - <<'PY'
import json, re

d = json.load(open('/tmp/xiaoice_detail.json', encoding='utf-8'))
if d.get('code') != 200:
    print('业务失败:', d.get('code'), d.get('message')); raise SystemExit(1)

x = d['data']
print('virtualHumanId    :', x.get('virtualHumanId'))
print('defaultVoiceId    :', x.get('defaultVoiceId'))
print('supportTransparency:', x.get('supportTransparency'))
print('category          :', x.get('category'))

print()
print('=== 姿态 postureInfos（virtualHumanPostureId 用这里的 bizId）===')
for p in (x.get('postureInfos') or []):
    url = p.get('previewPicture') or ''
    base = url.rsplit('/', 1)[-1]
    m = re.search(r'_(\d+)x(\d+)\.', base)
    dim = '%sx%s' % m.groups() if m else '未解析出尺寸'

    # 按预览图等比缩放并居中放入 1080x1920 画布 —— 直接给出可用的 attributes
    if m:
        sw, sh = int(m.group(1)), int(m.group(2))
        scale = min(1080 / sw, 1920 / sh)
        w = int(round(sw * scale)); h = int(round(sh * scale))
        if w % 2: w += 1
        if h % 2: h += 1
        attrs = 'width=%d, height=%d, x=%d, y=%d' % (w, h, (1080 - w) // 2, (1920 - h) // 2)
    else:
        attrs = '无法计算，请查 previewPicture 实际尺寸'

    print('  %-14s %-16s %-12s -> attributes: %s' % (p['bizId'], p['name'].strip(), dim, attrs))

print()
print('=== 声音 voiceInfos（voiceId 用这里的 voiceId）===')
for v in (x.get('voiceInfos') or []):
    print('  %-24s %-14s %-8s %-8s %s' % (
        v.get('voiceId'), v.get('displayName'), v.get('gender'),
        v.get('language'), (v.get('auditionFile') or '')[:60]))

print()
print('提示：把上面某个 bizId 作为 virtualHumanPostureId、voiceId 作为 tts.voiceId，')
print('      配合本脚本算出的 attributes 即可提交（见 04/05 脚本）。')
PY
