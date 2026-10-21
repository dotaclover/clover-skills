# 百炼 DashScope 协议（qwen-image 系列）

> 依据阿里云百炼官方《千问-图像生成与编辑 API 参考》（2026-10 版）整理。文中标「实测」的是我们跑过的；其余是官方规格。

qwen-image 有**三种官方接入方式**，模型能力一致：

| 接入方式 | 端点 | 适用 |
|---|---|---|
| OpenAI 兼容 | `{base}/compatible-mode/v1/images/generations` | 已有 OpenAI Images 代码，改 base_url 和 model 即可 |
| DashScope 同步 | `/api/v1/services/aigc/multimodal-generation/generation` | 推荐，功能最全 |
| DashScope 异步 | `/api/v1/services/aigc/image-generation/generation` + 轮询 | 批量、不想长时间占用连接 |

兼容模式是**同步非流式**，不支持异步、流式、partial image、`/images/edits`、multipart、mask。要这些能力就走 DashScope。

## 一、地域

**模型、Endpoint URL、API Key 必须同属一个地域**，跨地域调用会失败。

| 地域 | 域名 |
|---|---|
| 华北2（北京） | `https://dashscope.aliyuncs.com` |
| 新加坡 | `https://dashscope-intl.aliyuncs.com` |
| 美国（弗吉尼亚） | `https://dashscope-us.aliyuncs.com` |
| 德国（法兰克福） | `https://dashscope-eu.aliyuncs.com` |
| 日本（东京） | `https://dashscope-jp.aliyuncs.com` |

官方推荐换业务空间专属域名（性能与稳定性更好）：`https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com`，其他地域同理换成 `{WorkspaceId}.{region}.maas.aliyuncs.com`。

## 二、模型

| 模型 | 文生图 | 图生图 | 参考图上限 | 说明 |
|---|---|---|---|---|
| `qwen-image-3.0-pro` | ✅ | ✅ | 3 张 | 3.0 Pro，质量最高 |
| `qwen-image-3.0` | ✅ | ✅ | 3 张 | 3.0 标准版，兼顾质量与速度 |
| `qwen-image-2.1-pro` | ✅ | ✅ | **10 张** | 2.1 Pro，I2I 支持更多参考图，可自动输出带透明通道的图 |
| `qwen-image-2.1-turbo` | ✅ | ✅ | **10 张** | 2.1 Turbo，性价比最优 |

- 输出统一 PNG，分辨率可指定，总像素 512×512 至 2048×2048，**不指定 `size` 时由模型按提示词自动推荐**。
- `qwen-image-2.0` / `2.0-pro` 属上一代，字段与 2.1 一致，仍可用；可选模型以控制台地域列表为准。

## 三、P2 同步接口

```
POST {base}/api/v1/services/aigc/multimodal-generation/generation
Content-Type: application/json
Authorization: Bearer $DASHSCOPE_API_KEY
```

### 文生图

```json
{
  "model": "qwen-image-3.0",
  "input": {
    "messages": [
      { "role": "user", "content": [{ "text": "一只橘猫坐在窗台上，午后阳光，简洁插画风格" }] }
    ]
  },
  "parameters": {
    "size": "1024*1024",
    "n": 1,
    "negative_prompt": "文字，水印，模糊",
    "prompt_extend": true,
    "watermark": false
  }
}
```

### 图生图

同一个端点，`content` 数组里先图后字：

```json
{
  "model": "qwen-image-3.0",
  "input": {
    "messages": [
      {
        "role": "user",
        "content": [
          { "image": "https://example.com/in.png" },
          { "text": "把这张图改成水彩画风格，保留构图和主体" }
        ]
      }
    ]
  },
  "parameters": { "n": 1, "size": "1024*1024" }
}
```

三条硬规则：

1. **只能有一个 `text`**，不传或传多个都报错。
2. **图的数量**：2.1 系 1–10 张，3.0 系 1–3 张，按数组顺序即「图一 / 图二」。
3. **输出比例以最后一张输入图为准**，`size` 不决定比例。

### 请求字段

| 字段 | 必填 | 说明 |
|---|---|---|
| `model` | 是 | 见上表 |
| `input.messages` | 是 | 只能一个元素，`role` 固定 `user` |
| `content[].text` | 是 | 正向提示词，推荐 ≤4500 Token |
| `content[].image` | 图生图必填 | 公网 URL 或 `data:{MIME};base64,{data}` |
| `parameters.size` | 否 | `宽*高`，**星号**。总像素 512×512 ~ 2048×2048，宽高比 1:8 ~ 8:1 |
| `parameters.n` | 否 | 1–6，默认 1，必须整数 |
| `parameters.negative_prompt` | 否 | ≤500 字符，**仅 3.0 系支持** |
| `parameters.prompt_extend` | 否 | 默认 `true`，会改写提示词 |
| `parameters.prompt_extend_mode` | 否 | `direct`（默认，T2I/I2I 都可）/ `agent`（仅 T2I，I2I 传会 400） |
| `parameters.enable_thinking` | 否 | 默认 `true`，仅在 `prompt_extend=true` 时生效，会增加耗时 |
| `parameters.watermark` | 否 | 默认 `false` |
| `parameters.seed` | 否 | 0–2147483647，相对稳定 |

图像输入要求：JPG / JPEG / PNG / BMP / TIFF / WEBP / GIF；宽高 1–8000px（建议 384–2048）；长宽比 ≤10:1；单张 ≤10MB。

### 响应

```json
{
  "output": {
    "choices": [
      {
        "finish_reason": "stop",
        "message": {
          "role": "assistant",
          "content": [{ "image": "https://...png?Expires=..." }]
        }
      }
    ]
  },
  "usage": {
    "output_width": 1024,
    "output_height": 1024,
    "input_image_count": 1,
    "input_image_type": "qima_input_1k",
    "output_image_count": 1,
    "output_image_type": "qima_output_1k"
  },
  "request_id": "571ae02f-..."
}
```

- `usage` 是**图片计量**，不是 token 用量。3.0 系用 `output_width`/`output_height`/`*_image_count` 这组；2.1 系用 `width`/`height`/`image_count`，字段名不一样，解析要分支。
- 失败时才有 `code` / `message`，成功时这两个字段不出现。
- 只回 URL，PNG，24 小时过期。

## 四、P3 异步接口

端点和同步**不同**，但请求体**相同**（都是 `input.messages`）。

### 第一步：创建任务

```
POST {base}/api/v1/services/aigc/image-generation/generation
X-DashScope-Async: enable
Content-Type: application/json
Authorization: Bearer $DASHSCOPE_API_KEY
```

请求体与 P2 同步完全一样，`size` 也用星号，`n` 同样支持 1–6。返回：

```json
{ "output": { "task_status": "PENDING", "task_id": "0385dc79-..." }, "request_id": "..." }
```

漏了 `X-DashScope-Async: enable` 会报 `current user api does not support synchronous calls`——看着像权限问题，其实是头没加。

### 第二步：轮询

```
GET {base}/api/v1/tasks/{task_id}
Authorization: Bearer $DASHSCOPE_API_KEY
```

状态：`PENDING` → `RUNNING` → `SUCCEEDED` / `FAILED` / `CANCELED` / `UNKNOWN`。`task_id` 有效期 24 小时，官方建议间隔约 10 秒。

**必须用提交任务时的地域、业务空间和 Key 查询**，不能跨地域。

成功响应里图同样在 `output.choices[0].message.content[0].image`，**不是** `results[].url`（那是旧版文生图接口的写法）：

```json
{
  "output": {
    "task_id": "17d7d840-...",
    "task_status": "SUCCEEDED",
    "submit_time": "2026-08-07 15:50:14.837",
    "end_time": "2026-08-07 15:50:33.607",
    "choices": [
      { "message": { "role": "assistant", "content": [{ "type": "image", "image": "https://...png" }] } }
    ]
  },
  "usage": { "output_width": 1024, "output_height": 1024, "output_image_count": 1 },
  "request_id": "..."
}
```

失败时 `task_status` 是 `FAILED`，原因在 `output.code` / `output.message`。

## 五、OpenAI 兼容层（走 P1 时的 qwen 专属字段）

端点：`{base}/compatible-mode/v1/images/generations`，请求体平铺在顶层，没有 `input` / `parameters` 嵌套。

| 字段 | 说明 |
|---|---|
| `model` / `prompt` | 必填 |
| `image` | **图生图字段**。URL 或 `data:...;base64,...`，字符串或数组。不传 = 文生图 |
| `size` | `1024x1024`（**字母 x**）或 `auto` |
| `n` | 1–6，整数 |
| `negative_prompt` | 仅 3.0 系 |
| `prompt_extend` / `prompt_extend_mode` / `enable_thinking` / `watermark` / `seed` | 与 DashScope 同义 |

兼容模式返回：

```json
{
  "created": 1788339600,
  "data": [{ "url": "https://...png?Expires=..." }],
  "usage": { "output_width": 1024, "output_height": 1024, "input_image_count": 1, "output_image_count": 1 }
}
```

- 图生图**不走** `/images/edits`，也不支持 multipart 和 mask。用 `/images/edits` 是另一套协议，行为不同。
- 不返回 `request_id`，它在响应头 `x-request-id`；用 OpenAI Python SDK 时读 `response._request_id`。
- `response_format: b64_json` 会被忽略，仍返回 URL。
- 用 OpenAI SDK 传扩展字段要放 `extra_body`。

**实测注意**：第三方兼容层不一定实现上面这些。我们测过一个只认 `/images/edits`、忽略 `image` 字段的服务，详见 `references/models.md`。

## 六、错误码

| code / 报错 | 含义 | 处理 |
|---|---|---|
| `InvalidApiKey` / `No API-key provided.` | Key 缺失、拼错、或跨地域 | 核对 Key 与地域，别重试 |
| `InvalidParameter` / `n must be 1` | 该模型不支持多张 | 检查模型与 `n` |
| `current user api does not support synchronous calls` | 异步端点漏了 `X-DashScope-Async` | 加请求头 |
| `InvalidParameter` / `Field 'prompt' is required` | `prompt` 为空 | 补提示词 |
| `prompt_extend_mode` 传 `agent` + I2I | 该组合不支持 | 图生图用 `direct` |
| `DataInspectionFailed` | 内容审核拦截 | 改提示词，别重复提交 |
| `Throttling` / 429 | 限流 | 退避后重试一次 |

## 七、坑

- **图只有 URL，24 小时过期，不支持 base64。** 拿到就下载转存。
- **`prompt_extend` 默认开着。** 用户说「生成的不是我描述的」，先看异步结果的 `rewrite_status`，再把 `prompt_extend` 设 `false` 对比一次。
- **同步与异步的端点不同，请求体相同。** 别把同步地址加个异步头就用，会 404。
- **异步结果在 `choices`，不在 `results`。** 照旧文生图文档写的解析代码会取到空。
- **3.0 系与 2.1 系的 `usage` 字段名不同**（`output_width` vs `width`），写通用解析要兼容两套。
- **兼容模式不支持 `/images/edits`。** 想用 multipart 只有第三方的兼容层才会提供，且行为（尤其 `size`）与官方不同。
