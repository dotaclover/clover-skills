# 分层验收与排障

## 测试级别

| 层级 | 检查 | 能证明什么 |
|---|---|---|
| 静态 | 路由、类型、配置解析器、模型映射 | 代码存在相应实现 |
| 离线 | 限定包单测、mock、前端 typecheck/build | 在指定环境下回归通过 |
| 只读 HTTP | status、models | 服务可达且指定认证/模型列表可用 |
| 真实推理 | 一次最小文本、流式或任务 | 指定模型/账号/协议在当时可用 |
| 业务 | 额度、租户、日志、结算退款 | 本次链路符合业务规则 |

不能用 models 成功、文档说明或单元测试通过宣称所有线上模型可用。

## 只读 HTTP 示例

下面使用 PowerShell；变量由用户在当前进程提供，示例不包含真实 Key。不自动执行；远端请求也要有授权。不要打印响应头中的凭据或把详细错误全量写入公开日志。

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:3201/api/status"
$gatewayHeaders = @{ Authorization = "Bearer $env:JUHE_GATEWAY_TOKEN" }
Invoke-RestMethod -Uri "$env:JUHE_GATEWAY_BASE_URL/v1/models" -Headers $gatewayHeaders
$cpaHeaders = @{ Authorization = "Bearer $env:JUHE_CPA_TOKEN" }
Invoke-RestMethod -Uri "http://127.0.0.1:12301/v1/models" -Headers $cpaHeaders
```

将 `JUHE_GATEWAY_BASE_URL` 设置为不带尾部 `/v1` 的服务地址。`JUHE_*` 只是此处测试命令的变量名，不表示两个业务项目内置支持这些环境变量。

## 授权后单次文本验收

先让用户明确模型、环境、次数和可能费用。模型名必须取自授权的模型配置，不猜测。以下命令只提交一次非流式 Chat：

```powershell
$payload = @{
    model = $env:JUHE_TEST_MODEL
    messages = @(@{ role = "user"; content = "Reply OK only." })
    stream = $false
} | ConvertTo-Json -Depth 8
Invoke-RestMethod -Method Post -Uri "$env:JUHE_GATEWAY_BASE_URL/v1/chat/completions" -Headers $gatewayHeaders -ContentType "application/json" -Body $payload
```

Responses、Messages、流式和工具调用是额外测试，不因为上面命令通过就自动批量执行。测试不写真实客户数据；需要最大输出限制时按目标协议与模型支持设置字段，不一概强加不支持的参数。

## 必验清单

- [ ] 网关用户令牌与 CPA 服务 Key 不可互换；错误认证返回明确拒绝。
- [ ] 对外模型映射到预期渠道/上游模型，分组没有串线。
- [ ] GPT Responses / Chat、Claude Messages 按真实客户端分别通过。
- [ ] SSE 能逐段到达；客户端取消后上游及时释放，不在代理中长时间缓冲。
- [ ] 工具参数、call ID、结束原因正确，不因重试重复执行有副作用的工具。
- [ ] OAuth 失效、额度耗尽、上游 429/5xx 有明确处理；不无限重试。
- [ ] 同一会话粘性符合配置，故障切换后行为可解释。
- [ ] usage、输入/输出/缓存计费、分组倍率和用户余额一致。
- [ ] 商户 Host 正确解析，跨租户令牌/任务查询被阻断。
- [ ] 视频任务成功结算、失败退款、重复轮询幂等；不重复创建任务。
- [ ] 管理 API、公网端口、凭据目录和日志权限符合部署约定。

## 故障定位表

| 症状 | 优先检查 |
|---|---|
| 401 / 403 | 先分清网关 Token、CPA 服务 Key、上游凭据和管理 Key；再查租户/分组/初始化状态 |
| 模型列表空 | CPA 实际 auth-dir、工作目录、已授权账号与模型权限；网关分组和渠道 Models |
| models 有、推理失败 | 模型映射、协议是否支持、上游权限和真实 usage；不要只改模型展示名 |
| 404 | origin 是否重复附加 /v1、/v2、/api/v3；新旧配置与二进制是否一致 |
| GPT Chat 可用但 Codex 失败 | Responses、compact、工具协议、流式事件和账号权限 |
| Claude Messages 失败 | 网关渠道协议、x-api-key/anthropic-version 传递、CPA 账号授权、模型别名 |
| SSE 一次性返回 | Nginx/CDN 缓冲、压缩、超时和客户端读取方式 |
| 请求耗时很长 | 网关重试 × CPA 账号重试、冷却等待、流式首包和网络超时 |
| 启动后账号池为空 | 相对 auth-dir、服务工作目录、目录访问权限、是否启动错误配置 |
| 配置改了无效 | v8 字段覆盖旧字段、运行版本、加载文件、网关渠道缓存 |
| 视频一直 queued | 轮询服务、task_id 与渠道绑定、供应商查询路径/状态转换，不重新提交 |
| 余额异常 | usage、预扣/结算、缓存倍率、视频退款幂等、租户倍率和币种 |
| 修改 Host 后 403 | 租户解析、平台域名、商户状态与 setup 状态 |

## 交付记录

每次维护输出：目标环境/分支、变更文件、渠道/协议矩阵、测试命令与脱敏结果、费用与任务数、未验证项、回滚步骤。未知内容明确标为未知，不用历史文档替代当前运行状态。
