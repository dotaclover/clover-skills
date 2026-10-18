---
name: aigc-image-2
description: 通过 juhe.top 的 OpenAI 兼容图片接口列出图片模型、生成海报或其他图片、保存 Base64 或 URL 结果并记录可复现请求。适用于用户要求通过 juhe.top 测试或调用 GPT Image 系列图片生成 API；不用于视频生成。
agent_created: true
---

# Juhe.top OpenAI 图片生成（GPT Image）

通过 Juhe.top 的 OpenAI 兼容接口生成图片。执行真实付费请求前确认用户已经提供 API Key，并从用户要求中提取模型、提示词、尺寸和数量。一次请求成功后不要自动生成更多变体；只有用户明确要求时才追加付费生成。

## 接口

```text
Base URL: https://juhe.top/v1
列出模型: GET  https://juhe.top/v1/models
生成图片: POST https://juhe.top/v1/images/generations
鉴权: Authorization: Bearer $JUHE_API_KEY
```

已验证可见的图片模型：

- `gpt-image-2`：已完成真实生成测试，支持 `1024x1536` 竖图。
- `gpt-image-2.5-flare`：模型列表可见，尚未完成真实生成验证。
- `gpt-image-2.5-sunburst`：模型列表可见，尚未完成真实生成验证。

模型可用性可能随账号变化。用户没有指定模型时，先调用 `GET /v1/models`；若 `gpt-image-2` 可用，默认用它完成兼容性测试。

## 必须遵守

1. 真实 Key 仅放入环境变量或请求头，不在最终回复、公开 curl 和日志摘要中回显，也不写入技能文件。
2. 保存一份以 `<JUHE_API_KEY>` 代替真实 Key 的 curl 记录。
3. 默认 `n: 1`，避免无意中产生多张图片和额外费用。
4. HTTP 200 后解析 `data[0]`。优先处理 `b64_json`，也兼容 `url`。
5. 收到 `b64_json` 时必须进行 Base64 解码后保存为图片文件，不能把整段 Base64 直接显示给用户。
6. 收到 `url` 时保存原始响应和 URL；仅在当前执行环境允许且用户已授权该生成任务时下载结果。
7. 保存请求 JSON、脱敏 curl、原始响应和最终图片；报告 HTTP 状态、模型、尺寸、文件路径及返回类型。
8. 请求失败时保留原始错误并分析，不要未经用户要求更换模型反复付费尝试。

## 超时陷阱（实测）

图片生成单张耗时约 40 秒，慢时超过 2 分钟。**默认 120 秒前台超时会把 curl 中断（SIGTERM），但服务端可能已经跑完并计费。**

- 生成请求一律加 `--max-time 480`，并放到后台执行，完成后取结果。
- 被中断的请求不要立刻重试，先检查响应文件是否已写入，避免重复扣费。

## 标准流程

### 1. 查询模型

```bash
curl "https://juhe.top/v1/models" \
  -H "Authorization: Bearer $JUHE_API_KEY"
```

从 `data[].id` 筛选包含 `image`、`seedream`、`dall`、`flux`、`imagen` 或其他明显图片模型名称的条目。不要仅根据名称声称模型已经生成验证。

### 2. 构造请求

将请求保存为 `image-request.json`：

```json
{
  "model": "gpt-image-2",
  "prompt": "Design a premium vertical technology poster for NexGate AI. Dark blue background, orange and electric blue data streams, a futuristic gateway, clear commercial typography, polished enterprise SaaS advertising style, no third-party logos, no watermark.",
  "size": "1024x1536",
  "n": 1
}
```

提示词应明确主体、用途、构图、视觉风格、文字内容、品牌色、画幅及禁止元素。若用户要求海报中的精确文字，把文字逐项写入提示词；生成后仍需目视检查拼写。

### 3. 生成图片

```bash
curl -X POST "https://juhe.top/v1/images/generations" \
  -H "Authorization: Bearer $JUHE_API_KEY" \
  -H "Content-Type: application/json" \
  --max-time 480 \
  --data-binary "@image-request.json" \
  -o image-response.json
```

最小兼容字段为 `model`、`prompt`、`size` 和 `n`。不要为兼容性测试擅自加入供应商私有参数。

### 4. 保存结果

Base64 返回通常类似：

```json
{
  "created": 1790707938,
  "data": [
    {
      "revised_prompt": "...",
      "b64_json": "...",
      "width": 1024,
      "height": 1536
    }
  ]
}
```

实测 `gpt-image-2` 同时返回 `width` / `height`，**不返回 `url`**，不要假设两者同时存在。

Node.js 解码示例：

```javascript
const fs = require('fs');
const response = JSON.parse(fs.readFileSync('image-response.json', 'utf8'));
fs.writeFileSync('generated-image.png', Buffer.from(response.data[0].b64_json, 'base64'));
```

URL 返回通常类似：

```json
{
  "data": [
    {
      "url": "https://example.com/generated-image.png"
    }
  ]
}
```

签名 URL 可能过期，应提示用户及时下载或转存。

## OpenAI SDK 示例

Python：

```python
import base64
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["JUHE_API_KEY"],
    base_url="https://juhe.top/v1",
)

result = client.images.generate(
    model="gpt-image-2",
    prompt="A premium vertical NexGate AI technology poster",
    size="1024x1536",
    n=1,
)

image_bytes = base64.b64decode(result.data[0].b64_json)
with open("nexgate-ai-poster.png", "wb") as output:
    output.write(image_bytes)
```

如果 SDK 对象未暴露 `b64_json` 但返回 `url`，改为读取 `result.data[0].url`，不要假设两者同时存在。

## 结果检查

生成完成后检查：

- 文件可以正常解码和打开。
- PNG 宽高（`buf.readUInt32BE(16)` / `buf.readUInt32BE(20)`）与请求尺寸一致。
- 主体、构图、品牌色和用途符合提示词。
- 海报文字没有拼写错误、乱码或缺字。
- 没有用户禁止的 Logo、水印或其他元素。

文字有误但整体构图可用时，先向用户展示结果并说明具体问题。只有用户要求修改时才生成下一张。

## 报告格式

向用户报告：

- Key 鉴权是否成功，不显示 Key 本身。
- `/v1/models` 是否成功及相关图片模型。
- 图片生成 HTTP 状态和实际使用模型。
- 请求尺寸、返回类型、文件大小和本地图片链接。
- 脱敏 curl、请求 JSON 和原始响应的保存位置。
- 任何文字、画面或兼容性限制。
