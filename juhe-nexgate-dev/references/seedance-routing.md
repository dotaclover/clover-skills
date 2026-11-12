# Seedance：公开协议、上游路由与模型映射

核对基线：`C:/code/mcwlapi` 的 `dev` 提交 `4d373b0d6`（2026-11-12）。这是源码状态，不代表该版本已部署；国际版需要独立确认。

## 不要混淆两段协议

```text
客户：POST /api/v3/contents/generations/tasks
      model=doubao-seedance-2-0-mini-260615，content=[...]
  → 方舟兼容中间件转为内部任务 → 鉴权、按模型/分组分配渠道
  → 百度 V2（46）：Fire V2，默认 model=S2.0-Mini
    或火山方舟（45）：Ark，默认 model=客户原 ID
  → 客户收到 {"id":"task_..."}，之后仍向网关原路径 GET 查询
```

- `router/video-router.go`：公开 POST/GET `/api/v3/contents/generations/tasks`；原有 `/v1/video/generations` 与 `/v1/videos` 也保留。
- `middleware/volcengine_video_adapter.go`：保留客户原 body 到 `metadata`，改变内部请求表示，不强制选择火山渠道。
- `relay/relay_task.go:RelayTaskSubmit`：在渠道选定后读取 `info.ChannelType`，Seedance 仅允许 46/45，按类型确定任务平台。
- `relay/channel/task/doubao/adaptor.go`：同一适配器分别实现 Fire V2 与 Ark；两者都用选中的上游 Key 做 Bearer 鉴权。
- 查询通过已保存任务的渠道与上游 ID 进行，不重新按模型随机分配上游。`DoResponse`、`ConvertToVolcengineVideo` 对客户返回平台公开 ID 和原模型名，不暴露私有上游任务 ID。

此次未更改公开路由、成功响应结构、公开模型 ID 约定。但拒绝旧渠道类型、frames 边界、执行期限与未知状态的行为有变化，不能宣称所有外部行为完全零变化。

## 模型映射在哪里

顺序是：先按客户模型选渠道，再读取该渠道 `model_mapping`，最后由适配器构建上游 body。

1. **渠道自定义映射优先**：后台“编辑渠道 → 模型与分组 → 模型映射（Model Mapping）”。字段 `model_mapping`；`relay/helper/model_mapped.go:ModelMappedHelper` 支持链式映射，检测循环。生效后直接使用最终目标，不再追加百度内置转换。
2. **百度内置映射**：没有生效的自定义映射时，使用 `relay/channel/task/doubao/constants.go:baiduFireModelMapping`；由 `BuildRequestBody` 调用。
3. **方舟无内置 Fire 转换**：无自定义映射时沿用客户模型 ID；有自定义映射时用其目标，例如账号已开通的模型/接入点 ID。

| 客户模型（短别名与对应版本均覆盖） | 百度默认目标 |
| --- | --- |
| `doubao-seedance-2-0` / `doubao-seedance-2-0-260128` | `S2.0` |
| `doubao-seedance-2-0-fast` / `doubao-seedance-2-0-fast-260128` | `S2.0-Fast` |
| `doubao-seedance-2-0-mini` / `doubao-seedance-2-0-mini-260615` | `S2.0-Mini` |
| `doubao-seedance-2-5` / `doubao-seedance-2-5-260628` | `S2.5` |

百度标准模型一般不需要手工填映射。若已有自定义目标是旧 VOD 模型或错误名称，它会覆盖默认转换；排障时检查后台实际配置，不凭截图推定为空。自定义目标也不应只映射到另一个 `doubao-seedance-*` 别名再期待内置表继续处理。客户模型始终用于公开路由与计费标识；日志中“请求模型”和“实际模型”不同是正常适配现象。

## 渠道地址与执行行为

| 渠道 | Base URL 示例 | 创建路径 |
| --- | --- | --- |
| 百度 V2 / 46 | `https://qianfan.baidubce.com` | `/v2/mm/fire/generations/tasks` |
| 火山方舟 / 45 | `https://ark.cn-beijing.volces.com` | `/api/v3/contents/generations/tasks` |

查询在创建路径后追加供应商私有任务 ID。Base URL 不重复添加版本路径。类型决定协议，不是供应商域名白名单；任意地址仅改类型不能变成正确的上游。旧 DoubaoVideo / 54 的注册仍存在，但提交 URL 和 FetchTask 已拒绝此类型；在途旧任务不能假设自动兼容。

- `model.InitTask` 为 45/46 保存提交时选中的 Key；后续轮询使用任务私有 Key，避免多 Key 串账号。严禁把该字段放进诊断 DTO、日志或技能。
- Fire 默认 48 小时；网关默认 `TASK_TIMEOUT_MINUTES=1440`。新百度请求显式设置 `execution_expires_after` 不超过平台期限；上游最低 3600 秒、最高 259200 秒。旧任务不会自动修改执行期限。
- 本地超时退款不等于上游取消。本次没有调用上游取消接口；不承诺彻底消除供应商最终完成与本地退款之间的竞态。
- `frames` 有界校验并参与预扣估算；终态按上游 usage 结算。未知状态不再长期伪装成 running。

## 日志与验证

管理员任务列表的“任务诊断”显示私有上游 ID、原 request_id、供应商、URL、提交 body/response、最近轮询时间/次数、HTTP 状态、上游请求 ID、轮询错误和响应。消费日志在终态或本地超时后补充最终快照；退款保留自身幂等结算 ID，并可通过诊断原 request_id 关联提交。

429/5xx/网络失败也会持久化最近诊断；仅保存最近快照，不宣称完整逐次轮询历史。复用 `private_data`/`other` JSON，无新增列或 ENV。普通用户与公开任务查询不增加私有诊断；已有历史 ID 可显示，未采集的历史请求与轮询内容无法恢复。

关键实现：`service/task_polling.go`、`service/task_billing.go`、`model/task.go:PersistTaskPollTrace`、`controller/task.go:tasksToDto`、`web/default/src/features/usage-logs/components/task-trace-details.tsx`。

基线验证包含本地定向回归、Go build、前端类型检查/lint/build；没有使用本轮改动进行线上付费视频验证。真实验收需要同一公开请求分别命中指定百度/方舟渠道，核对上游 ID、模型、终态、计费与失败退款，按用户授权控制生成数量。VOD 后续恢复见 [历史记录](vod-history.md)。
