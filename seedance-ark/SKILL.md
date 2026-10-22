---
name: seedance-ark
description: 直连火山方舟官方 Seedance 视频与私域素材 API，使用 API Key 调用视频、AK/SK 签名管理素材，实测排查已授权人像查询、H5 认证、素材引用和授权期限问题。用于官方渠道，不用于第三方兼容渠道或客户网关。
agent_created: true
---

# Seedance：火山方舟官方直连

把视频推理、已有授权素材查询、新建 H5 认证分别验证；不要因为某一步成功或失败就推断另两步的能力。

## 最短工作流

1. 先读 [实测记录](references/verification.md)，区分已验证事实、当前账号限制和未验收功能。
2. 按 [接口与示例](references/api.md) 核对域名、凭据、项目、Action/Version。密钥仅从环境或本机忽略的 `.env` 读取，不输出真实 Key、SK、Token、H5 链接或带签名的素材 URL。
3. 先运行只读查询，再在用户已授权的范围内创建 H5、素材或收费视频。使用 `scripts/seedance.py`：素材调用自动计算 HMAC，写操作须显式 `--allow-write`，视频创建须 `--allow-charge`。这些开关不是用户授权本身。
4. 报告真实 HTTP 状态、上游错误码、RequestId、模型及终态；任务创建返回 ID 只代表接收，必须查询到终态才算生成验收。

## 关键边界

- 视频：`ark.cn-beijing.volces.com/api/v3`，`ARK_API_KEY`，Bearer。
- 素材：`ark.cn-beijing.volcengineapi.com`，`ARK_ASSET_ACCESS_KEY` + `ARK_ASSET_SECRET_KEY`，HMAC V4，`cn-beijing` / `ark` / `2024-01-01`。不要把 AK 当 Bearer，也不要混用控制台 BFF 的版本号。
- 素材查询默认项目来自 `ARK_ASSET_PROJECT_NAME`，未配置时为 `default`；项目名大小写敏感。
- `ListAssetGroups` 为空、普通 `GetAsset` 404，不足以证明控制台已授权素材不存在。已知授权组可尝试实测可用的 `ListAuthorizedFirstAssetByGroups`；它每组最多返回一个符合条件的素材，不是完整组发现或全量素材清单。
- 官方控制台创建/接收的真人素材可查询，不代表当前账号能调用 `CreateVisualValidateSession`。后者当前实测返回 `SubscriptionRequired`，不可解释成全部素材权限都失效。
- H5 `BytedToken` 为 30 分钟、单次认证凭证，不是肖像授权期限。公开 H5 API 没有确认 `authorization.valid_days` 等期限字段；控制台能设置期限不等于 API 支持。
- `CallbackURL` 是授权人点击完成后的浏览器 GET 回跳；服务端再调用 `GetVisualValidateResult` 核验，不信任浏览器提供的成功码。不得把未扫码查询的 404 当作授权成功或已确认的正常 Pending。
- 不自动删除既有真人素材，不把删除等同于撤回肖像授权。只针对用户明确指定的测试资源执行删除，保留上游失败结果。
- 多用户系统在业务侧记录会员、渠道、项目与组/素材归属，禁止账号级库存自动归到所有用户；视频请求只能引用本用户合法授权的 `asset://`。

视频字段、素材请求和 cURL 见 [references/api.md](references/api.md)。需要说明“现在究竟哪些可用”时，以 [references/verification.md](references/verification.md) 中对应端点和账号的真实结果为准；其他渠道结果不能移作官方证据。
