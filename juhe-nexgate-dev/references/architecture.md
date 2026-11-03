# 架构与责任

## 目标拓扑

```text
WorkBuddy / Codex / Claude Code / 业务客户端
                  |
          HTTPS + 用户网关令牌
                  v
         Nginx → mcwlapi (new-api)
                  |
      +-----------+-----------+------------+
      |           |           |            |
    百度         阿里         火山         mcwlcpa
    千帆       DashScope      Ark         CLIProxyAPI
                                           |
                                    GPT/Codex、Claude
                                     合法授权账号池
```

保持 mcwlapi 为统一业务入口。CPA 的客户端 Key 只供网关内部使用；业务客户端不直连 CPA，以免绕过网关权限、额度与审计。

国内 dev 与国际 internal 是同一网关历史的不同工作树，后者位于 C:/code/mcwlapi_internal；mcwlcpa 则是独立账号池项目。双版共享修复用有选择的 cherry-pick，保留各自币种、充值与部署差异。

## 分工

| 层 | 负责 | 不负责 |
|---|---|---|
| Nginx | TLS、Host/转发头、长连接、流式透传 | 模型定价和账号选择 |
| mcwlapi | 用户、租户、API Token、渠道、模型映射、分组、价格、预扣/结算/退款、日志 | OAuth refresh token 的长期管理 |
| 国内供应商 adaptor | 协议、鉴权、请求路径、usage/错误、任务状态转换 | 把所有渠道强制改成同一原生协议 |
| mcwlcpa | 账号授权、令牌更新、可用性、轮询/粘性、协议转换 | 替代网关的客户账本 |

## 四层凭据

1. 用户网关令牌：用于调用 mcwlapi，绑定网关用户、分组与额度。
2. CPA 服务 Key：配置在 CPA 的客户端鉴权列表，也写入对应 mcwlapi 渠道；GPT/Claude 分实例时分别设置。
3. 上游凭据：百度/阿里/火山渠道 Key 或 CPA 授权账号文件；禁止写入技能、Git、公开日志或 ZIP。
4. CPA 管理 Key：仅用于管理接口；与客户端 API Key 分离，默认不开放远程管理。

区分账号授权文件与普通渠道 Key：OAuth refresh token 不能直接填入网关渠道 Key。订阅账号权限不等于任意官方 API 模型权限，必须实际检查模型清单和授权范围。

## 推荐落地

- 国内供应商分别建渠道；同一模型允许按显式渠道/分组配置冗余，但不要未授权跨供应商转发用户数据。
- GPT/Codex 走 CPA OpenAI 兼容入口；Claude 按客户端需要验证 Anthropic Messages。
- 可采用 GPT、Claude 两个 CPA 实例实现凭据隔离；历史部署的 12302 是 Gemini/Claude 组，不要未经确认直接改成 Claude 专用组。
- 明确公网部署区域与供应商地域规则；“国内版”指业务网关与国内供应商接入方案，不代表所有账号服务可从任意区域访问。
- 记录协议兼容矩阵：Chat、Responses、Messages、工具调用、流式、usage 分别验收。可列出模型不等于全部协议都可用。

## 配置清单

交付渠道时至少记录：环境、租户/分组、渠道类型、Base URL、对外模型名、上游模型名、请求协议、凭据引用、价格单位、超时、重试、故障降级规则。只记录凭据存储位置，不记录真实值。
