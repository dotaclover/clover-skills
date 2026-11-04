# 图片生成与编辑

按 SKILL.md 复用已有凭据，不为示例重复索取或覆盖 Key。图片型号见 [模型清单](models.md)。需要提交后立即拿 task_id 时读 [异步图片](async-images.md)，先确认服务已启用；本页是同步生成/编辑。

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
- 超时/524 可能来自网络、反代、排队或上游，不足以断定型号不可用，也不表示未生成/未扣费。保留请求 ID，先核查原结果；不自动换型号或重提，见 [排障](troubleshooting.md)。
- 用户明确要求横向测试时才发额外生成，先核对不同型号支持的参数，不假设只改 model 总能兼容。
- `b64_json` 响应体常在 2–4 MB，务必用 `--output` 写入文件后解码，不要直接把响应读进变量或终端管道。
- URL 可能有签名和有效期，应及时保存；下载失败先重新获取原结果或联系服务方，不能自动重新生成。

### 保存生成结果

图片响应可能在 `data[]` 中返回 `b64_json` 或 `url`。下面使用 Python 3 保存第一张图：

```bash
python - <<'PY'
import base64
import json
from urllib.parse import urlsplit
from pathlib import Path
from urllib.request import urlopen

result = json.loads(Path('image-response.json').read_text(encoding='utf-8'))
item = result['data'][0]
if item.get('b64_json'):
    data = base64.b64decode(item['b64_json'], validate=True)
else:
    if urlsplit(item['url']).scheme != 'https':
        raise SystemExit('先核实媒体下载地址，不能把非 HTTPS 或本地路径当作图片 URL')
    # 媒体 URL 下载不附带网关 Authorization。
    with urlopen(item['url'], timeout=60) as response:
        data = response.read()
Path('image.png').write_bytes(data)
print('已保存 image.png')
PY
```

这是 Bash heredoc 写法；PowerShell 请把 Python 内容保存为 UTF-8 .py 文件再运行。异步结果从 result.data 读取，且必须先检查 status=completed，不套用同步顶层 data。

### 编辑已有图片

使用 `POST /v1/images/edits`，以 multipart 上传图片文件。让 curl 自动设置 multipart 的 `Content-Type`。

OpenAI 兼容适配器向上游转发真实二进制文件；多参考图用重复 `image[]` 字段并按顺序上传。图片响应中的 `b64_json` 是返回格式，不能据此把参考图上传改成 JSON base64。需要异步参考图时见 [async-images.md](async-images.md)，并先确认 multipart 扩展已部署。

客户端也可直接发送 JSON：`images:[{"image_url":"data:image/png;base64,..."}]`，可选 `mask:{"image_url":"data:image/png;base64,..."}`，其他 model/prompt/size/n 字段不变。这与 CPA 的 image-2/image-2.5 专用执行器所用结构一致。新版异步接口同样支持该结构，限制与部署边界见 async-images.md；输入不使用 b64_json。multipart 客户端继续上传文件，CPA 按执行器需要内部转换。

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
