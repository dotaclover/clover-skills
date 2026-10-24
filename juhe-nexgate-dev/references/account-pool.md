# mcwlcpa：GPT / Claude 授权账号池

## 先核实版本

代码根：`C:/code/mcwlcpa`。项目为 CLIProxyAPI，入口 `cmd/server/main.go`。

当前主模板 `config.example.yaml` 已采用 **v8 分层布局**；`config.standard.example.yaml`、`config.premium.example.yaml` 和历史部署文档可能仍使用旧布局。先比较当前配置解析器与运行二进制版本，再决定使用哪一套。不要用旧教程覆盖正在工作的 v8 配置。

| 用途 | v8 字段 | 旧版字段 |
|---|---|---|
| 监听 | `server.host` / `server.port` | `host` / `port` |
| 管理 | `management` | `remote-management` |
| 下游客户端 Key | `access.api-keys` | 顶层 `api-keys` 列表 |
| OAuth 凭据目录 | `oauth.auth-dir` | `auth-dir` |
| 路由/会话粘性 | `routing.*` | 按对应旧模板核实 |
| 重试 | `routing.retry.*` | 顶层 request-retry 等旧字段 |

v8 的顶层 `api-keys` 还可能代表上游 API Key 分组，不能把它当旧版客户端 Key 列表使用。

当前模板说明：新旧拼写并存时 v8 值优先，包括 false、0 和空集合；仅设置 `config-version: 8` 或 GET 管理接口不迁移旧文件，成功的 `/v8/management` 配置写入会执行迁移。修改前备份并审阅差异，不依靠自动迁移猜测结果。

## v8 最小结构示例

这是待配置的结构，不是可直接投产配置。把占位 Key 换成独立随机值；YAML 不保证展开 `${ENV}`，不要把环境变量占位符直接当成有效 Key。

```yaml
config-version: 8
server:
  host: "127.0.0.1"
  port: 12301
management:
  allow-remote: false
  secret-key: ""
  disable-control-panel: true
access:
  api-keys:
    - "REPLACE_WITH_PRIVATE_GATEWAY_TO_CPA_KEY"
routing:
  strategy: "round-robin"
  session-affinity: true
  session-affinity-ttl: "1h"
  session-affinity-subagents: true
  retry:
    request-retry: 1
    max-retry-credentials: 2
    max-retry-interval: 5
oauth:
  auth-dir: "./auths-gpt"
```

- `secret-key: ""` 用于禁用管理 API；需要管理时在私有配置中设置独立管理 Key，不要直接发布公网。
- 重试值为建议起点，不是源码默认值或容量承诺。与网关重试一起核算端到端预算。
- 新建 Claude 专用实例时可选 12302 与 `auths-claude`；如端口已由历史 Gemini/Claude 组占用，先保留现状并规划迁移。
- 使用绝对 auth-dir 或固定工作目录，避免服务从不同目录启动后加载空账号池。
- 容器内的 `127.0.0.1` 不是宿主机。分容器部署需要私有网络和正确服务地址，不能把回环示例机械照抄。

## 登录与授权

源码已核实 flags：`--config`、`--codex-login`、`--codex-device-login`、`--claude-login`、`--no-browser`。实际二进制名按构建产物核实，下面假定为 `cliproxyapi.exe`：

```powershell
.\cliproxyapi.exe --config "C:/private/cpa-gpt.yaml" --codex-login
.\cliproxyapi.exe --config "C:/private/cpa-claude.yaml" --claude-login
.\cliproxyapi.exe --config "C:/private/cpa-gpt.yaml"
```

仅在用户明确授权后执行登录；允许用户自行完成交互授权。不得收集账号密码、验证码或批量导入来历不明的 token。设备登录和无浏览器模式分别按 `--help` 与当前授权流程确认。

确保授权写入对应实例的 auth-dir。凭据目录不要同步到 skills、仓库或普通交付 ZIP；备份也必须限制权限。

## 路由策略

- `round-robin`：可用账号轮询，适合基本均衡。
- `weighted-round-robin`：按账号权重选择；具体权重位置与限制以当前配置为准。
- `fill-first`：优先填充可用账号，不等于最大并行能力。
- `session-affinity`：会话绑定账号，利于上下文/缓存；账号不可用时仍允许故障切换，不承诺永远使用同一账号。
- 子代理继承粘性可能提升缓存命中，也可能使单账号承担更高并发；按负载测试调整。
- 不通过增加重试或轮换账号规避供应商额度/权限。区分短时故障、额度耗尽、授权失效和请求本身错误。

## 网关对接

1. 在 CPA 验证目标账号池模型和协议。
2. 在 mcwlapi 创建渠道，服务地址指向 CPA 实例，渠道 Key 对应 `access.api-keys` 中的私有值。
3. 分别验证 `/v1/chat/completions`、`/v1/responses`、`/v1/messages` 中实际要使用的接口。
4. 确认客户端会话信息、工具调用、流式与 usage 没有被网关转换丢失。
5. 对外只发布网关令牌，不把 CPA 服务 Key、管理 Key 或 OAuth 凭据发给客户。

## 进一步定位

- 登录 flags：`cmd/server/main.go`。
- 配置兼容：`internal/config/`，搜索 `config-version`、`auth-dir`、`session-affinity`。
- HTTP 路由：`internal/api/`，搜索 `/v1`、`responses`、`messages`。
- 账号路由与执行：在 `internal/`、`sdk/` 内按 `selector`、`session`、`codex`、`claude` 搜索，先定位再修改。
- 不读取真实 auth JSON 来学习结构；优先看类型、测试和示例。
