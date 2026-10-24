---
name: juhe-nexgate-dev
description: 用于 Juhe 国内版 mcwlapi 与 mcwlcpa 的自用开发、渠道集成、模型映射、计费、部署和故障排查。以 new-api 为 API 网关接入百度、阿里、火山，以 CLIProxyAPI/clientproxyapi 为授权 GPT/Codex、Claude 账号池扩展。涉及这两个代码目录或国内版架构维护时触发；不用于客户 juhe-nexgate 运行时调用。
agent_created: true
metadata:
  version: 1.0.0
  scope: personal-development
---

# Juhe 国内版开发

## 固定边界

- 将 `C:/code/mcwlapi` 作为国内版主网关代码库；将 `C:/code/mcwlcpa` 作为 CLIProxyAPI 账号池代码库。允许用户指定替代路径，先核实再操作。
- 采用 `客户端 → mcwlapi → 国内供应商 / mcwlcpa → 授权账号池`。把用户、租户、令牌、模型权限、定价、额度和消费日志留在网关，把账号授权、轮询、会话粘性和失效切换留在 CPA。
- 区分四层凭据：用户网关令牌、网关到 CPA 的服务 Key、供应商 Key/OAuth 凭据、CPA 管理 Key；禁止互换。
- 保留 `juhe-nexgate` 客户交付包不变；不要从中复制客户配置或把 `juhe.top` 当国内版默认部署地址。
- 仅处理有合法授权的账号；遵守供应商服务条款、地域限制和额度限制。不要把账号池当作绕过限制的工具。
- 不自动读取 `.env`、真实 `config.yaml`、`auths*/`、OAuth JSON、Cookie 或 SSH 私钥。确需定位配置时先确认文件范围，输出只保留脱敏字段。
- 不擅自部署、执行登录、批量探测或生成计费请求；先说明目标、调用次数、可能费用和写入范围，再取得授权。

## 按任务加载

| 任务 | 参考文件 |
|---|---|
| 总体架构、责任和凭据边界 | [architecture.md](references/architecture.md) |
| mcwlapi 开发、路由、模型、计费、租户 | [gateway-development.md](references/gateway-development.md) |
| 百度、阿里、火山适配差异 | [domestic-providers.md](references/domestic-providers.md) |
| GPT/Claude 账号池、v8/旧版配置 | [account-pool.md](references/account-pool.md) |
| 本地环境、Nginx、发布和回滚 | [deployment.md](references/deployment.md) |
| 分层验收、排障与交付清单 | [verification.md](references/verification.md) |

## 最短工作流

1. 核实两个仓库的当前分支、工作树和涉及文件；不要默认切换分支，不覆盖用户已有修改。
2. 按责任层定位问题：客户端协议、网关路由/计费、CPA 账号池、国内上游；读取对应参考文件和当前源码。
3. 写出最小改动：对外模型名、上游模型名、渠道类型、Base URL、凭据来源、协议、计费单位、测试范围。
4. 优先复用现有 adaptor、任务流、路由与配置解析；不要为了接渠道引入新的代理层或重写用户/计费系统。
5. 先跑限定包的离线测试，再在授权后做单次真实验收；分清静态核实、测试通过与线上可用，不把三者混为一谈。
6. 交付变更文件、验证结果、未验证项和回滚办法；技能维护完成后同步本地用户技能与 `clover-skills/juhe-nexgate-dev`，仅提交本次技能相关修改。

## 事实来源优先级

以当前源码与配置解析器为准，其次为仓库示例，最后为历史部署文档。参考文件记录创建时核实的入口，不保证未来模型、价格、端点或运行版本不变。特别注意 CPA 主模板已经采用 v8，旧 standard/premium 示例仍可能是兼容布局；不要只修改 `config-version` 就认为完成迁移。
