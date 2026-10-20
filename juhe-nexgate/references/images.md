# 图片生成与编辑

先设置 SKILL.md 中的环境变量。图片型号与请求入口见 [模型清单](models.md)。

## 1. Image-2 系列

| 型号 | `model` |
|---|---|
| Image-2 | `gpt-image-2` |
| Image-2.5 Flare | `gpt-image-2.5-flare` |
| Image-2.5 Sunburst | `gpt-image-2.5-sunburst` |

### 文字生成图片

使用 `POST /v1/images/generations`，请求体为 JSON。

| 字段 | 类型 | 说明 |
|---|---|---|
| `model` | string，必填 | 图片型号 |
| `prompt` | string，必填 | 图片内容描述 |
| `n` | integer | 生成数量，示例为 `1` |
| `size` | string | 图片尺寸，示例为 `"1024x1024"` |

```bash
curl --silent --show-error --fail-with-body \
  --connect-timeout 30 --max-time 300 \
  "$JUHE_BASE_URL/v1/images/generations" \
  -H "Authorization: Bearer $JUHE_API_KEY" \
  -H 'Content-Type: application/json' \
  --data '{
    "model": "gpt-image-2",
    "prompt": "极简产品插画，一片绿色叶子，纯白背景，无文字。",
    "n": 1,
    "size": "1024x1024"
  }' \
  --output image-response.json
```

替换 `model` 即可请求另外两款 Image-2.5 型号。生成结果从 `data[]` 中读取，按响应中的 `b64_json` 或 `url` 保存。

### 超时与响应体积

- 图片生成本身耗时远高于文本，`--max-time` 建议设 `180`–`300` 秒。默认无限等待会让故障请求一直挂着。
- 设到 300 秒仍无任何响应、或返回 524，属于该型号上游问题，继续加大等待无效，按 [常见报错与处理](troubleshooting.md) 中的“单型号无响应判定”换型号。
- 同一提示词横向测试型号时只改 `model`，其余字段保持一致，便于对比耗时。
- `b64_json` 响应体常在 2–4 MB，务必用 `--output` 写入文件后解码，不要直接把响应读进变量或终端管道。
- `url` 形式的结果链接带签名和有效期，生成后及时下载保存，过期后需重新生成。

### 保存生成结果

图片响应可能在 `data[]` 中返回 `b64_json` 或 `url`。下面使用 Python 3 保存第一张图：

```bash
python - <<'PY'
import base64
import json
from pathlib import Path
from urllib.request import urlopen

result = json.loads(Path('image-response.json').read_text(encoding='utf-8'))
item = result['data'][0]
if item.get('b64_json'):
    data = base64.b64decode(item['b64_json'])
else:
    with urlopen(item['url'], timeout=60) as response:
        data = response.read()
Path('image.png').write_bytes(data)
print('已保存 image.png')
PY
```

### 编辑已有图片

使用 `POST /v1/images/edits`，以 multipart 上传图片文件。让 curl 自动设置 multipart 的 `Content-Type`。

```bash
curl --silent --show-error --fail-with-body \
  "$JUHE_BASE_URL/v1/images/edits" \
  -H "Authorization: Bearer $JUHE_API_KEY" \
  -F 'model=gpt-image-2' \
  -F 'prompt=把叶子的颜色改成蓝色，保留纯白背景。' \
  -F 'n=1' \
  -F 'size=1024x1024' \
  -F 'image=@image.png' \
  --output image-response.json
```

按前一节解码保存编辑结果。

## 2. Qwen 与 Wan 图片

`qwen-image-3.0`、`wan2.7-image-pro` 的文字生成使用同一 JSON 请求格式，例如：

```bash
curl --silent --show-error --fail-with-body \
  "$JUHE_BASE_URL/v1/images/generations" \
  -H "Authorization: Bearer $JUHE_API_KEY" \
  -H 'Content-Type: application/json' \
  --data '{
    "model": "qwen-image-3.0",
    "prompt": "一片绿色叶子的极简插画，纯白背景，无文字。",
    "n": 1,
    "size": "1024x1024"
  }' \
  --output image-response.json
```

响应含 `data[0].url` 时下载该地址；含 `b64_json` 时解码保存。

`wan2.6-image` 使用参考图片。已有图片可使用上面的 multipart 编辑请求，将 `model` 改为 `wan2.6-image`。编辑结果按响应中的 `data[]` 保存。

此型号也可使用以下带参考图片的 JSON 请求格式：

```bash
curl --silent --show-error --fail-with-body \
  "$JUHE_BASE_URL/v1/images/generations" \
  -H "Authorization: Bearer $JUHE_API_KEY" \
  -H 'Content-Type: application/json' \
  --data '{
    "model": "wan2.6-image",
    "prompt": "让光线更温暖，保留画面主体和构图。",
    "n": 1,
    "size": "1024x1024",
    "input": {
      "messages": [{
        "role": "user",
        "content": [
          {"image": "https://example.com/reference.png"},
          {"text": "让光线更温暖，保留画面主体和构图。"}
        ]
      }]
    }
  }' \
  --output image-response.json
```

将图片 URL 替换为真实可访问地址。每个 `content` 元素分别放 `image` 或 `text`，不要在同一元素内同时填写两者。
