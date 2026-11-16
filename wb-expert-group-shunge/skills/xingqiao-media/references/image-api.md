# 星桥 · 图片接口备忘

来源：服务方《图片 API · 第三方对接文档》2026-10-26 版，只保留调用要用的部分。服务地址 `https://api.novqiao.com`。

保留供应商原始 `cost_usd` 字段与报价币种；实际结算币种和换算比例由当前账号合约及账单确认，不默认 1:1。报价不锁价。


## 接口

| 方法 | 路径 | 结果 |
|---|---|---|
| GET | `/v1/image-v2/models` | 当前 Key 可用的模型与参数能力 |
| POST | `/v1/image-v2/quote` | 询价，不生成不预扣 |
| POST | `/v1/image-v2/references` | 上传参考图，201 返回 `resource_id` |
| POST | `/v1/image-v2/tasks` | 建任务，202 |
| GET | `/v1/image-v2/tasks/{task_id}` | 查任务 |
| 待确认 | `/v1/image-v2/tasks/query`（历史 POST）或 `/v1/image-v2/tasks?ids=...`（其他资料 GET） | 资料冲突，不猜方法或自动试写；向服务方确认当前契约，暂用单任务 GET |
| GET | `/v1/image-v2/images/{resource_id}/content` | 原鉴权下载，须同一提交 Key |
| GET | `/v1/media/callbacks/signing-key` | 回调验签密钥 |

鉴权：`Authorization: Bearer sk-...`，`/v1/image-v2/*` 需开通图片任务能力、模型权限和额度。

## 模型目录字段

`{"object":"list","data":[...]}`，每项：`model`／`is_default`（原样提交模型名）、`sizes`／`pixel_sizes`／`uses_pixel_size`／`max_pixels`、`aspect_ratios`、`qualities`、`output_formats`、`max_images`／`max_reference_images`、`operations`、`supported_parameters`／`unsupported_parameters`。

**单模型限制优先，不要用全局最大值替代。**

## 询价

请求体与创建任务相同：

```json
{"model":"...","prompt":"白色陶瓷杯","size":"1024x1024","n":1,"quality":"high"}
```

返回 `{"model","operation","price_spec","n","unit_price_usd","estimated_cost_usd","currency":"USD","quoted_at"}`。

预计值含客户倍率，**不锁价、不留额度**；缺价报真实错误，不默认免费。最终以任务 `cost_usd` 为准。

## 创建任务字段

| 字段 | 要求 |
|---|---|
| `prompt` | 必填非空 |
| `model` | 建议显式传目录里的完整模型名 |
| `n` | 1–4，模型上限可能更低 |
| `size` | 像素如 `1024x1024`，或模型允许的 `auto` |
| `image_size` | `1K`／`2K`／`4K` 档位 |
| `aspect_ratio` | 与 size 一致 |
| `quality` | 来自目录 `qualities`，不是都有 `high` |
| `output_format` | png／jpeg／webp |
| `images` | 图生图，HTTPS 地址数组 |
| `image_reference_ids` | 上传所得数字 ID，1–16，与 `images` 互斥 |
| `response_format` | `url`／`b64_json` |
| `callback_url` | 可选公网 HTTPS，不传用 Key 已配的回调 |

暂不支持：`mask`、`background`、`output_compression`、`partial_images`、`moderation`、`input_fidelity`、`style`、`transparent_output`、`nsfw`、流式。

## 幂等

`Idempotency-Key`：1–128 个可打印 ASCII、不含空白。同 Key、同入口、同幂等键、同请求在 24 小时内返回原任务，重放带 `Idempotency-Replayed:true`。同键改参数 → 409 `IDEMPOTENCY_KEY_CONFLICT`；同键仍在受理 → 409 `IDEMPOTENCY_IN_PROGRESS`，按 `Retry-After` 重试。不带该头则每次提交都建新任务。

**新业务必须用新键**；超过 24 小时别靠键找回，用存下的 `task_id`。

## 状态机

| status | state | 动作 |
|---|---|---|
| `queued` | `waiting` | 继续查 |
| `running` | `generating` 等 | 继续查 |
| `succeeded` | `completed` | 读 `data` 下载 |
| `failed` | `failed` | 读 `error`，停止自动重试 |

以 `terminal` + `next_action` + `retry_after_seconds` 为准。处理中附带的错误信息不是终态；等久了也不要重新提交。

成功结果：

```json
{"task_id":123,"status":"succeeded","terminal":true,"next_action":"read_result",
 "cost_usd":0.125,"data":[{"resource_id":31,
 "url":"https://.../v1/image-v2/images/31/download?ticket=...","url_expires_at":1793048400}]}
```

## 下载

- 结果里的 `url` 是 24 小时签名链接，直接 GET，**不要附 Bearer**，可能 307 到存储域。
- 过期用原 Key 重查任务拿新链接，**不要重新生成**。
- 旧 `/content` 入口仍可带 Bearer 读。
- 部分历史结果只有 `url` 或 `b64_json`，按实际字段读。

## 错误

| HTTP／code | 处理 |
|---|---|
| 400 `IMAGE_PARAMETER_UNSUPPORTED`／`IMAGE_MODEL_UNAVAILABLE` | 重读目录改参数，不自动换模型 |
| 400 `IMAGE_PRICE_NOT_CONFIGURED` | 找服务方补价格，不视为免费 |
| 401／403 | Key、分组、模型权限、钱包额度 |
| 404 `IMAGE_TASK_NOT_FOUND` | 核 ID 与原密钥 |
| 409 `IDEMPOTENCY_KEY_CONFLICT` | 同一业务沿用原请求，新业务换键 |
| 429 | 按 `Retry-After` 退避，已受理的继续查 |
| 503／504 且已有 task_id | 查任务，不重新生成 |
| `IMAGE_UPSTREAM_OUTCOME_UNKNOWN` | 结果不确定，停止提交并联系服务方 |

## 回调（按当前任务选择并授权部署）

终态 POST 到 `callback_url`，外层同查询响应，事件名 `image_task.completed`／`image_task.failed`。至少一次语义，最多 5 次（5／15／45／120 秒退避），按 `X-Sub2API-Idempotency-Key` 去重，10 秒内回 2xx。

验签：`v1=` + HMAC-SHA256(signing_key, timestamp + "." + 原始正文字节) 的小写 hex，时间差 ≤300 秒，恒定时间比较。**必须用原始字节，重新序列化 JSON 会变**。
