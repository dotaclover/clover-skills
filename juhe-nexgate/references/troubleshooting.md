# 接口故障与重试

先记录服务地址（不含凭据）、方法/路径、模型、HTTP 状态、task_id、request_id 和脱敏错误。不要将完整提示词、Key、签名 URL 或 base64 粘贴到公开日志。CLI 错误输出 http_status（存在时），不需要从错误字符串猜测。

| 现象 | 下一步 |
| --- | --- |
| 400 | 核对路径、请求类型、字段、数量/尺寸；异步图片需要幂等 key 且不支持 stream=true |
| 401 | auth status 检查来源，环境变量覆盖安全存储；确认失效后才更换凭据，网络错误不当作失效 |
| 403 | 检查模型/租户/Token 权限，或服务端状态 |
| 404 | 核对 Base URL 和部署；图片查询还需原 Token/租户，不一定是任务不存在 |
| 409 | 图片幂等 key 对应不同原始请求，恢复原文件；不要自动换 key |
| 429 | 区分限流、活跃任务数量与额度；查询原任务，不连续重提创建 |
| 503 | 图片异步可能未启用，联系服务方；不自动回退同步生成 |
| 5xx / 520–527 / 网络超时 | 请求可能已处理。查询可以有限重试；创建按下方幂等边界恢复 |
| HTTP 200 | 只证明 HTTP 成功；文本检查 finish_reason，任务检查 status，不能据此宣称完成 |
| pending / processing / queued / running | 间隔查原 ID，设置客户端总等待期限；到期保留 ID |
| failed / cancelled / expired | 停止轮询，检查错误；不自动生成替代任务 |
| needs_review | 图片生成/账务不确定，停止重提，提供 request_id 给服务方核查 |
| 媒体 URL 失效 | 先重查原任务或联系服务方取结果，不自动重建；下载不带网关 Key |

## 按操作恢复

- **异步图片提交**：没有收到 ID 时，用同一服务、同一 Token、同一 Idempotency-Key、相同原始 JSON 字节重发。已有 ID 则只 GET。不要更换 JSON 序列化格式、key、型号或转同步。CLI 不自动重试。
- **同步图片/视频创建**：未明确支持幂等时不能保证安全重发。保留请求 ID，先核查是否已创建/扣费。另一次生成必须有用户授权，不能当作免费诊断。
- **查询**：GET 可在总等待期限内有限重试，例如 2、5、10 秒退避，尊重 Retry-After。不清除凭据；客户端等待结束不代表服务端取消。
- **已有异步任务**：直接查询，不强制 models/resolve；原 Token 额度耗尽/过期仍可能有只读权限。
- **模型可见但失败**：列表、文本协议、图片协议是不同证据。文本成功不能证明图片通道故障；仅凭超时不能判断型号不可用，更不能承诺换型号成功。

## 参数与客户端

- 根地址不带 /v1，逐路径拼接；OpenAI SDK 一般使用 base_url=<根地址>/v1。
- Responses 的 POST 存在不代表 background/get/cancel 已接好，未确认不发送 background=true。
- 图片编辑 multipart 让客户端生成 boundary，不手写 Content-Type: multipart/form-data。
- 视频的 Ark 与 OpenAI 格式不能混用 id/task_id、状态值、查询路径；按对应参考。
- 同步图片顶层 data[]；异步图片先 status=completed 再 result.data[]；不要把 JSON 当图片保存。
- finish_reason=length 是输出限制信号；按模型支持的参数调输出预算，不把所有空文本归为网络故障。
