# 图片异步任务与视频共用边界

核实基线：mcwlapi dev 的 `294492dec`、`f749e5139`（2026-11-03）。这是源码和本地验证，不表示 international 或公网已部署。先阅读仓库 `docs/2026-11-03-异步图片任务.md` 和下列实现。

| 责任 | 文件 |
| --- | --- |
| 提交/查询与入参 | `controller/async_image_task.go`、`router/relay-router.go` |
| 幂等、状态事务 | `model/async_image_task.go` |
| 队列、worker、响应捕获 | `service/async_image_task.go` |
| 普通生成/计费 | `controller/relay.go`、`relay/image_handler.go`、`service/billing.go` |
| 公共任务、视频隔离 | `model/task.go`、`relay/relay_task.go`、`controller/video_proxy.go` |
| 启动/退出 | `main.go` |

## API 与生命周期

`POST /v1/images/tasks` 接收普通生成 JSON，必须提供 `Idempotency-Key`，持久化后返回 HTTP 202、`task_id`、`status`、`request_id` 及 Location。task_id 由服务端生成。`GET /v1/images/tasks/:task_id` 使用同一租户/用户/Token，只读数据库，返回状态和原始 result。

幂等 key 为 1–128 个不含空格的 ASCII 可打印字符，在租户/用户/Token 内隔离。同 key 按原始请求字节及指定渠道计算摘要；改变 JSON 空白/字段顺序也可能 409。每用户 pending/processing 上限 10；请求 1 MiB、结果 64 MiB；n 复用 dto.MaxImageN。只支持生成 JSON，不支持 edits/multipart、stream=true 或取消。

图片状态 pending → processing → completed/failed/needs_review 对应公共 Task 的 QUEUED/IN_PROGRESS/SUCCESS/FAILURE/UNKNOWN。两表事务更新；Task 只含轻量元数据、result_endpoint 和实际 quota/channel/group，完整图片在扩展表。

## 视频隔离和计费

- `Platform=local_image`、`Action=image_generation`。共用用户/管理员/商户任务列表，本次不含前端图片预览或专用类型文案。
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
