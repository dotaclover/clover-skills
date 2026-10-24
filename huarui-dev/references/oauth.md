# GPT / WorkBuddy OAuth 规划边界

## 1. 现有基础

项目已有两条不同 OAuth 链路：

### Codex / GPT 上游授权

- `service/codex_oauth.go` 调用 OpenAI OAuth Token 端点刷新 access token。
- `service/codex_credential_refresh.go` 读取 Codex 渠道中的 OAuth JSON，刷新并回写 access token、refresh token、过期时间、账号 ID 和邮箱。
- `service/codex_credential_refresh_task.go` 等文件提供渠道凭据刷新任务相关基础。

这说明项目已有“上游账号授权凭据刷新”能力，但不等于已经完成面向普通用户的 GPT OAuth 登录页面、账号池、授权回调、并发租约、撤销和审计闭环。

### 平台用户身份 OAuth

- `controller/oauth.go` 负责登录、绑定、验证、CSRF state、会话校验和回调处理。
- `oauth/registry.go` 支持内置 Provider 和数据库驱动的通用自定义 Provider。
- 平台 OAuth 的结果是 CloverAPI 用户身份或绑定关系，和 GPT/Codex 的上游模型调用授权不是同一对象。

## 2. 未来设计前必须确认

1. 用户要登录 CloverAPI，还是要把自己的 GPT/Codex 账号授权给 CloverAPI 使用。
2. 授权主体是一人一账号、管理员账号池，还是按渠道轮换。
3. refresh token 的加密存储、撤销、轮换、过期、并发刷新和失败隔离策略。
4. 上游服务条款、账号授权范围、地区/组织权限及用户明确同意。
5. WorkBuddy OAuth 是否存在正式可使用的身份或授权协议；不能因为用户写作 `workbuyy` 就假设协议、Client ID、回调地址或 scope。

## 3. 不应直接承诺的内容

- 不能把当前 Codex refresh 函数称为“GPT OAuth 登录已完成”。
- 不能把平台自定义 OAuth Provider 当作 OpenAI/Codex 上游授权适配器。
- 不能把 WorkBuddy OAuth 写成已支持；目前只列为未来探索方向。
- 不能在技能、日志或示例中写入 refresh token、access token、授权码、Cookie 或真实邮箱。

## 4. 建议实施路线

先形成不含凭据的设计：授权对象和生命周期、回调状态、密文存储、token refresh worker、并发锁、账号健康状态、用户撤销、审计和故障降级；再决定是否新增 Provider/Controller/Model，而不是直接复用平台登录表。
