# 两个出图供应商

> 实测时间 2026-10-30。地址、模型、字段都以当天实际响应为准，不凭印象。
> Key 不写进本文件，也不写进请求体、响应、报告或最终回复。

## 一、供应商 A：sub.aicodexvip.top（默认）

```
Base URL: https://sub.aicodexvip.top/v1
协议:     OpenAI 兼容（同步）
模型:     gpt-image-2 / gpt-image-2.5-flare / gpt-image-2.5-sunburst
```

### 接口

| 用途 | 方法与路径 |
| --- | --- |
| 文生图 | `POST /v1/images/generations` |
| 图生图 | `POST /v1/images/edits`（multipart） |
| 列模型 | `GET /v1/models` |

最小请求体：

```json
{"model": "gpt-image-2", "prompt": "...", "size": "1024x1024", "n": 1}
```

返回 `data[].b64_json`（base64 PNG），偶尔也带 `url`。三支模型结构完全一致，
换模型只改 `model`。

### 环境与规格核验

保留 curl 传输实现，但历史 UA 拦截、代理故障、3168px 宽度和尺寸量化现象不能视为永久协议。
默认尊重系统代理；仅在当前网络授权允许直连时，用全局参数 `--no-proxy <主机列表>`。
需要特定 UA 时显式 `--user-agent <值>`，不得用于绕过服务限制。
模型、尺寸、耗时与响应体大小以当前服务目录及实际响应为准；用 `save --expect-size` 核验。
`send --timeout` 默认 480 秒只是可调客户端预算，不代表供应商保证。


## 二、供应商 B：api.novqiao.com（备用）

```
Base URL: https://api.novqiao.com
协议:     专用图片队列 /v1/image-v2/*（异步任务）
```

### 接口清单

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/v1/image-v2/models` | 当前密钥可用的模型与能力参数 |
| POST | `/v1/image-v2/quote` | 询价，不生成不扣费 |
| POST | `/v1/image-v2/references` | 上传参考图，201 返回 resource_id |
| POST | `/v1/image-v2/tasks` | 创建任务，202 返回 task_id |
| GET | `/v1/image-v2/tasks/{task_id}` | 查询任务 |
| 待确认 | `/v1/image-v2/tasks/query` | 批量查询方法在历史资料中有 GET/POST 冲突，须向服务方确认当前契约，不提供可执行调用 |
| GET | `/v1/image-v2/images/{resource_id}/download?ticket=...` | 下载结果，无需 Bearer |
| GET | `/v1/image-v2/images/{resource_id}/content` | 原鉴权下载，须同一提交密钥 |
| GET | `/v1/media/callbacks/signing-key` | 取回调验签密钥 |

### 创建任务的请求字段

```json
{
  "model": "your-image-model",
  "prompt": "必填，非空文本",
  "size": "1024x1024",
  "image_size": "1K",
  "n": 1,
  "quality": "high",
  "output_format": "png",
  "aspect_ratio": "1:1",
  "images": ["https://..."],
  "image_reference_ids": [21],
  "response_format": "url",
  "callback_url": "https://your-app.example.com/hooks/images"
}
```

注意：
- `images` 与 `image_reference_ids` **互斥**
- `image_reference_ids` 1—16，且必须属于同一用户与同一密钥
- 尺寸开放与否**以模型目录为准**，未开放或未定价的规格在受理前就报错
- `image_size` 的 `1K/2K/4K` 档位要传**显式值**，别只写 size
- 专用队列**不支持** mask、background、output_compression、partial_images、
  moderation、input_fidelity、style、transparent_output、nsfw、流式生成

### 状态机

| status | state | 动作 |
| --- | --- | --- |
| queued | waiting | 继续查同一个 task_id |
| running | generating | 继续查同一个 task_id |
| succeeded | completed | 读 `data` 并下载 |
| failed | failed | 读 `error.code/message`，停止重试 |

**优先看 `terminal`、`next_action`、`retry_after_seconds`**，不要把处理中附带的
错误信息当终态，也不要因为等得久就重新提交——重新提交会再计费。

### 幂等键

`Idempotency-Key` 头，1—128 个可打印 ASCII 字符，不含空白。

- 同密钥 + 同入口 + 同幂等键 + 相同请求，24 小时内返回原任务
- 重放会加 `Idempotency-Replayed: true`
- 同键参数变了 → 409 `IDEMPOTENCY_KEY_CONFLICT`
- 同键还在受理中 → 409 `IDEMPOTENCY_KEY_IN_PROGRESS`，按 `Retry-After` 重试原请求
- **新的业务生成必须用新键**；超过 24 小时别指望原键找回，用已保存的 task_id

### 回调验签

```python
import hashlib, hmac, time

def verify_callback(headers, raw_body: bytes, signing_key: str) -> bool:
    timestamp = headers.get("X-Sub2API-Timestamp", "")
    signature = headers.get("X-Sub2API-Signature", "")
    try:
        if abs(time.time() - int(timestamp)) > 300:
            return False
    except ValueError:
        return False
    expected = "v1=" + hmac.new(
        signing_key.encode(), timestamp.encode() + b"." + raw_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected)
```

**`raw_body` 必须是收到的原始字节**，不能先解析再序列化。

回调是**至少一次语义**，可能重复，按 `X-Sub2API-Idempotency-Key` 去重。
回调最多 5 次，间隔约 5/15/45/120 秒。回调失败时**终态查询仍是恢复入口**。

### 下载

成功后 `data[]` 里是签名下载链接：

```json
{"data": [{"resource_id": 31, "url": "https://.../download?ticket=SIGNED_TICKET", "url_expires_at": 1793048400}]}
```

- 链接是临时凭证，**不要附加 API Key 到下载 URL**
- 过期后用原密钥查任务拿新链接，**不要重新生成**
- 结果也可能直接返回 `b64_json`，按实际字段读

## 三、错误处理

| 码 | 处理 |
| --- | --- |
| 400 `IMAGE_PARAMETER_UNSUPPORTED` / `IMAGE_MODEL_UNAVAILABLE` | 重新读模型目录改参数，**不自动换模型** |
| 400 `IMAGE_PRICE_NOT_CONFIGURED` | 联系服务方，**不视为免费** |
| 401 / 403 | 查密钥、分组、模型权限、钱包额度 |
| 404 `IMAGE_TASK_NOT_FOUND` | 查任务 ID 与是否用原密钥 |
| 409 `IDEMPOTENCY_KEY_CONFLICT` | 同业务保留原请求，新业务用新键 |
| 429 | 按 `Retry-After` 退避，已受理任务继续查 |
| 503 / 504 且已有 task_id | **查已有任务，不要重新生成** |
| `IMAGE_UPSTREAM_OUTCOME_UNKNOWN` | 结果不确定，停止自动重投，联系服务方核查 |

**只返回 HTTP 错误不等于任务没执行。** 有 task_id 就查它，别再发一遍。

## 四、通用坑

| 坑 | 说明 |
| --- | --- |
| 客户端超时 | 不证明服务端未执行；按网络与任务配置 `--timeout`，已有任务继续查询，不自动重投 |
| 少写 `/v1` 会返回前端 HTML | 状态码还是 200。先看响应体开头是 `{` 还是 `<` |
| `model_not_found` 常以 503 返回 | 不是 404，说明渠道没上这个模型 |
| `b64_json` 存在但是空字符串 | 判空值而不是判键是否存在 |
| `n>1` 可能只回一张 | 另一张藏在 `metadata.output.choices[].message.content[]` |
| 兼容层会静默丢弃 `image` 字段 | 传图出的是别的东西，HTTP 全程 200 |

## 五、脚本对照

| 动作 | 命令 |
| --- | --- |
| 列模型 | `image_api.py models --provider sub` |
| 询价 | `image_api.py quote --provider rrw --model X --size 1024x1024` |
| 上传参考图 | `image_api.py upload --provider rrw --file ref.png` |
| 创建任务 | `image_api.py send --provider rrw --model X --prompt "..." --size 1024x1024 --idempotency-key k1` |
| 轮询 | `image_api.py poll --provider rrw --task-id 123 --out-dir out` |
| 落盘核对 | `image_api.py save --response resp.json --out-dir out --expect-size 1024x1024` |
| 读尺寸 | `image_api.py size out/image-01.png` |
| 叠中文 | `image_api.py overlay --image out/image-01.png --text "文字" --out out/x.png` |
