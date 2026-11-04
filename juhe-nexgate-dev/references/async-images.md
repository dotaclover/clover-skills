# 图片异步任务与视频共用边界

核实基线：mcwlapi dev 的 `294492dec`、`f749e5139`（2026-11-03）。这是源码和本地验证，不表示 international 或公网已部署。先阅读仓库 `docs/2026-11-03-异步图片任务.md` 和下列实现。

2026-11-04 后续源码扩展 multipart 编辑；不是此前发布包能力。详见仓库 `docs/2026-11-04-异步参考图编辑.md` 和 `relay/helper/async_image_multipart.go`。部署后 `async_image_tasks` 自动新增 content_type/is_edit 两列；旧 JSON 任务继续走 generations，禁止旧 worker 与新版混跑。

| 责任 | 文件 |
| --- | --- |
| 提交/查询与入参 | `controller/async_image_task.go`、`router/relay-router.go` |
| 幂等、状态事务 | `model/async_image_task.go` |
| 队列、worker、响应捕获 | `service/async_image_task.go` |
| 普通生成/计费 | `controller/relay.go`、`relay/image_handler.go`、`service/billing.go` |
| 公共任务、视频隔离 | `model/task.go`、`relay/relay_task.go`、`controller/video_proxy.go` |
| 启动/退出 | `main.go` |

## API 与生命周期

后续补齐 JSON Base64 编辑：controller 调用 `helper.ValidateAsyncImageJSON`，存在合法 images 数组即 IsEdit=true，保留 application/json 与原始字节，worker 走 edits。结构为 `images:[{image_url:"data:image/png;base64,..."}]`，mask 为同结构对象；不使用输出字段 b64_json。1–16 图，单图解码 ≤20 MiB，总编码 JSON ≤64 MiB，无 images 的文生图仍 ≤1 MiB。验证严格 Base64、MIME 和 mask PNG，拒绝 URL/file_id/裸 Base64；DTO 正式 Images/Mask 字段透传，不转 multipart。CLI submit 同步扩容，JSON 幂等仍按原字节。上线状态仍需部署核验。

`POST /v1/images/tasks` 接收生成 JSON、Base64 参考图编辑 JSON 或 multipart 文件编辑，必须提供 `Idempotency-Key`，持久化后返回 HTTP 202、`task_id`、`status`、`request_id` 及 Location。task_id 由服务端生成。`GET /v1/images/tasks/:task_id` 使用同一租户/用户/Token，只读数据库，返回状态和原始 result。

幂等 key 为 1–128 个不含空格的 ASCII 可打印字符，在租户/用户/Token 内隔离。JSON 按原始字节及指定渠道计算摘要，改变空白/字段顺序可能 409。multipart 先规范化：字段排序、图片维持上传顺序、文件名和 MIME 统一、内容摘要决定 boundary；再把 edits 类型、Content-Type、渠道和规范 body 纳入摘要，重试换 boundary 不产生新任务。每用户 pending/processing 上限 10；JSON 请求 1 MiB，multipart 64 MiB，结果 64 MiB；不支持 stream=true 或取消。

multipart 允许 1–16 张 PNG/JPEG/WebP 参考图和可选一张 PNG mask，单文件 20 MiB；image/image[] 二选一，不接受 indexed 字段或重复 scalar。n 复用 dto.MaxImageN，size 复用普通 edits 校验/计费。网关接收上限不等于上游承诺。文件字节存扩展表 Payload，不存 Redis、不持久依赖本机临时路径；worker 恢复 edits 和完整 Content-Type，上游使用 multipart 文件。终态清空 Payload；公共查询和幂等查询不加载上传大字段。请求清理中间件负责 RemoveAll，覆盖进程内 worker；同请求复用 parsed form。

两跳格式要分开：网关 → CPA 接收层为 multipart 文件；CPA `internal/runtime/executor/codex_openai_images.go` 的 `codexRewriteOpenAIImageEditMultipartToJSON` 会把参考图转成 `images[].image_url` 的 Base64 Data URL、mask 转成 `mask.image_url`，用于 image-2/image-2.5 的专用上游；普通 `openai_compat_executor.go` 则继续 multipart。客户端不必跟随内部协议转换；本次不修改 CPA，实际生产 executor 需核查路由后才能断言。

图片状态 pending → processing → completed/failed/needs_review 对应公共 Task 的 QUEUED/IN_PROGRESS/SUCCESS/FAILURE/UNKNOWN。两表事务更新；Task 只含轻量元数据、result_endpoint 和实际 quota/channel/group，完整图片在扩展表。

## 视频隔离和计费

- `Platform=local_image`、`Action=image_generation` 或 `image_edit`。共用用户/管理员/商户任务列表，本次不含前端图片预览或专用类型文案。
- 未完成扫描、超时扫描、待计费扫描均排除 local_image。不能只在 adaptor 分发处跳过，因为此前可能已退款。
- 视频查询、内容代理、remix/续作原任务解析在访问渠道前拒绝图片 ID。
- worker 重新读取 Token/用户，进程内 handler 执行完整图片鉴权、限流、渠道和计费。内部 context 标识不能来自 HTTP Header；复用提交 RequestID、可信客户端 IP 和租户 Host。
- 复用普通图片结算，用进程内 receipt 确认成功，不相信上游响应头。内存 ResponseWriter 必须支持 Gin Flush，否则成功图片会在结算前 panic。

## Redis 与恢复

默认关闭：ASYNC_IMAGE_TASKS_ENABLED=true 才启用。要求 Redis 5+，启动检查 ZPOPMIN；默认 2 worker、范围 1–16，每进程生效；timeout 默认 600 秒、范围 30–3600。同库节点共享队列 key，不同库/版本部署隔离 key。

Redis ZSET 只存 ID，数据库拥有请求、结果和 pending→processing 的条件更新。每 30 秒补发 pending 通知。持久化成功但入队失败仍返回 202，等待 Redis 恢复。processing 不重排；期限加 60 秒后进入 needs_review。只重试结果保存，不重试上游生成。退出时停止领取，与 HTTP shutdown 并行等待。

提交不冻结额度，执行时使用当前配置预扣/结算；余额、Token、渠道变化可失败。普通 Relay 部分退款仍异步，needs_review 需按 request_id 核账，不承诺跨崩溃 exactly-once 或自动资金恢复。结果暂无自动清理，URL 仍有上游有效期。

## 最小验收

先 Redis 能力、迁移、HTTP，再按授权最小数量出图：立即返回 ID；状态推进；同 key 原请求仍同任务；换内容 409；另一 Token/租户查 404；耗尽 Token 可查询、禁用 Token 拒绝；公共/扩展状态一致；消费记录、Token 与 task quota 一致且只有一次；视频端点拒绝图片 ID。不通过真实杀死付费执行来“证明”崩溃资金安全。

本地 MySQL + Redis 7 + gpt-image-2 的一张 low/1024 图片已验证：约 20 ms 接收、28 秒完成、公共 SUCCESS、一条消费记录。不可把该耗时、价格或渠道健康度承诺给客户。
