# mcwlapi 网关开发

## 代码事实与定位

根目录：`C:/code/mcwlapi`。Go module 为 `github.com/QuantumNous/new-api`，当前 `go.mod` 声明 Go 1.25.1；运行前按本地文件核对工具链。前端位于 `web/default`，使用 Rsbuild。

| 领域 | 入口 |
|---|---|
| 路由总装配 | `router/main.go`、`main.go` |
| 文本和模型列表路由 | `router/relay-router.go` |
| 视频创建/查询 | `router/video-router.go` |
| 网关令牌鉴权 | `middleware/auth.go` |
| 渠道分发 | `middleware/distributor.go`（以实际目录核实文件名）及 `middleware` 内 Distribute 实现 |
| 渠道类型与默认 URL | `constant/channel.go` |
| 渠道管理 | `router/channel-router.go`、`controller/channel.go`、`model/channel.go`、`model/channel_cache.go` |
| adaptor 分发 | `relay/relay_adaptor.go` |
| 模型映射 | `relay/helper/model_mapped.go` |
| 视频任务流 | `relay/relay_task.go`、`service/task_polling.go`、`model/task.go` |
| 价格/分组倍率 | `setting/ratio_setting/model_ratio.go`、`group_ratio.go`、`relay/helper/price.go` |
| 账本/任务结算 | `service/billing.go`、`service/task_billing.go` |
| 租户上下文 | `middleware/tenant_context.go`、`model/tenant.go` |
| 教程内容 | `web/default/src/features/tutorials/`、`model/tutorial_seed.go` |

如果路径变化，先搜索函数或类型，不根据旧文档新建同名实现。

## 对外协议与链路

- `GET /v1/models`：令牌鉴权；按请求头识别 OpenAI、Anthropic 或 Gemini 模型列表。
- `POST /v1/chat/completions`：Chat Completions。
- `POST /v1/responses`：Responses；另有 `/v1/responses/compact`。
- `POST /v1/messages`：Anthropic Messages。
- `POST /api/v3/contents/generations/tasks`：Ark 原生风格视频任务提交。
- `GET /api/v3/contents/generations/tasks/:task_id`：任务查询。
- 视频还提供 `/v1/videos` 与 `/v1/video/generations` 系列接口；原生与兼容接口不要混用响应字段。

文本 relay 典型链路为：租户上下文 → 商户初始化检查 → TokenAuth → 模型请求限流 → Distribute → adaptor。模型列表不等于实际推理路由；列表成功后仍须独立验收推理。

Ark 请求经 `middleware/volcengine_video_adapter.go` 转成内部任务，保留原生参数，再由 task adaptor 处理。不要仅在 HTTP 路由里透传而绕开预扣、任务归属、轮询与结算。

## 配置一个渠道

1. 核实当前后台渠道表单和 `model.Channel`；优先通过已有后台/API 配置，不直接改生产数据库。
2. 选择协议相符的渠道类型；Base URL 按 adaptor 的拼接规则填写，一般只填 origin，防止重复 `/v1`、`/v2`、`/api/v3`。
3. 设置 `Models`、`Group`、`ModelMapping`、优先级/权重及渠道启用状态；字段支持情况以当前源码为准。
4. 使用“对外模型名 → 上游实际模型名”的 JSON 映射；禁止循环映射。同名模型是否具有相同上下文和工具能力，单独验证。
5. 配置价格、输出/缓存倍率和分组倍率；不要只加模型名却遗漏定价。
6. 检查渠道缓存更新机制，避免数据库已变更、实际分发仍用旧配置。

示例映射仅说明结构，不是可直接调用的模型：

```json
{
  "public-model-name": "actual-upstream-model-id"
}
```

## CPA 接入网关

- 先确认 CPA 实例的 `/v1/models` 和目标协议可用。
- 在网关创建协议匹配的兼容渠道，Base URL 指向 CPA 回环地址；网关渠道 Key 等于 CPA 客户端访问 Key，不是管理 Key。
- GPT/Codex 优先验收 Responses 与 Chat；Claude 优先验收 Messages。必要时按协议分别建渠道，不假设任意渠道自动支持三种协议。
- 核对流式转换、工具调用 ID、reasoning、finish reason、usage 和缓存统计；不要以 HTTP 200 代替业务正确性。
- 在网关和 CPA 两层控制重试预算，防止重试乘积导致高延迟和重复执行工具。

## 开发和测试

启动入口按目标依赖选择，参见 [deployment](deployment.md)；domestic-test.ps1 会关闭 Redis。前端使用 web/default、Bun、React 19/Rsbuild，按该目录 AGENTS 执行 typecheck/lint/build；不要假设存在 test script。

默认做 Go 构建和真实有限冒烟，自动化回归按当前任务及仓库要求选择。常用构建：

```powershell
go build ./...
```

测试先确认数据库、缓存状态和外部依赖；不盲目全包测试或付费探测。HTTP 200 不代表图片已生成、账务已完成。

## 租户与计费回归

- 核对请求 Host、`PLATFORM_HOSTS`、`TENANT_ROOT_DOMAIN`，检查商户初始化状态和租户隔离。
- 不用平台租户的成功结果代替商户租户验收。
- 文本检查输入、输出、缓存 usage；视频检查预扣、成功结算、失败退款及重复轮询的幂等性。
- 视频测试只创建一笔授权任务，后续复用同一 task_id；不要用反复提交代替轮询。
- 修改数据库结构遵循迁移惯例并验证目标数据库；按任务范围操作，不自动备份或恢复旧库。

## 代码约束速查

详细要求读取仓库 AGENTS，尤其这些容易遗漏的边界：

- JSON 编解码用 common.Marshal/Unmarshal/DecodeJson，不在业务代码直接调用 encoding/json。
- 数据访问兼容 SQLite/MySQL/PostgreSQL；行锁用 model 的 lockForUpdate，不写 GORM v1 query_option。
- 请求可选数值/布尔使用指针及 omitempty，保留显式 0/false。
- n、时长、max_tokens 等计费乘数使用已有上限，检查 multipart/Extra/metadata 旁路；quota 转换使用 common 的 checked helper，溢出审计留在 admin_info，不能裸 int(float) 产生负扣费。
- 表达式计费先读 pkg/billingexpr/expr.md；预扣、结算和退款全链路检查，不只看最终费用。
- LLM 日志在写入和历史展示时隐藏对话/推理/工具正文并保留 usage；图片/视频必须保留媒体结果 URL，不能套用文本脱敏导致结果消失。
- web/default 文案使用 i18n，维护六种语言；修改 UI 先读前端 AGENTS 及适用技能。不改未经要求的其他前端。

图片异步入口 POST /v1/images/tasks、GET /v1/images/tasks/:task_id，详见 [async-images](async-images.md)。与视频共用记录，不共用轮询/退款。
