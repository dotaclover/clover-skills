# 官方直连实测记录

记录日期：2026-10-21（北京时间）。这些结果属于本次配置的官方账号与项目，不代表所有账号、所有模型或百度兼容渠道。

## 1. 已有控制台真人素材查询

```http
POST https://ark.cn-beijing.volcengineapi.com/?Action=ListAuthorizedFirstAssetByGroups&Version=2024-01-01
```

- 鉴权：现有 IAM AK/SK，HMAC V4；Region `cn-beijing`，Service `ark`。
- 请求：已知 3 个 GroupId，`Statuses: ["Active", "Processing"]`，`ProjectName: default`。
- 结果：**HTTP 200，3 个素材均为 Image / Active / default**。
- RequestId：`20261021175507FDB4A89193C57056F218`。
- 本轮没有重新上传、修改或删除这 3 个真人素材。

用技能脚本再次执行相同只读查询也返回 **HTTP 200、3 个 Active**，RequestId 为 `202610211813306533B9C0448033C1748F`。普通 `ListAssetGroups` 的真人过滤查询返回 **HTTP 200、0 组**，RequestId 为 `20261021181242FC4D356CBADE33584700`，再次证明两类查询不能互相替代。

这证明当前 AK/SK 能从官方查询这些已授权素材。普通 `ListAssetGroups` 同时可返回 HTTP 200 空列表，不能据此推断没有素材。以上 Action 依赖已知组 ID，每组返回首个符合条件的素材；没有证明自动发现所有组或返回组内所有素材。

## 2. API 创建新的 H5 真人认证

```http
POST https://ark.cn-beijing.volcengineapi.com/?Action=CreateVisualValidateSession&Version=2024-01-01
```

标准请求只含 `CallbackURL` 和 `ProjectName: default`，**不带有效期参数**：

- 结果：**HTTP 403，`SubscriptionRequired`**。
- 官方消息：`This API requires an active subscription. Please subscribe to an advanced or premium plan.`
- RequestId：`2026102117461900F685307B55116A5BE1`。
- 本次没有成功生成官方 H5 链接，也没有真人完成认证。

技能脚本的标准无期限请求复测结果相同：HTTP 403 / `SubscriptionRequired`，RequestId 为 `20261021181330A24FE0F053F70B754BE5`。

带 `authorization.valid_days: 1` 及故意错误类型的探测同样先被订阅条件拦截。故此轮不能判定该期限字段被支持、被忽略或不合法；不能将错误归因为“必须删掉期限参数”，也不能把它解释成“当前账号所有素材接口都没有权限”。

## 3. 历史 H5 成功记录的渠道边界

已核对的本机 5 条 H5 成功会话均归属百度兼容渠道，不能作为官方直连成功证据。历史线上报告记录过成功返回 H5，但未记录足够渠道证据，不能据此认定官方成功或断言所有历史成功都来自百度。H5 可打开也不证明真人已同意、上游结果可查或素材绑定成功。

## 4. 本轮尚未验证成功的事项

| 能力 | 当前证据边界 |
|---|---|
| 官方 API 新建 H5 | 已实测 403，未创建成功 |
| H5 真人本人同意、完成回跳和绑定 | 未完成，需要真人本人操作 |
| API 设置肖像授权起止时间 / `valid_days` | 无公开字段依据；此次请求被订阅条件先拦截 |
| 四款候选模型逐项生成 | 尚未取得本轮完整创建与终态证据，不宣称全部可用 |
| 3 个已有真人素材用于生成视频 | 仅查询成功，未完成本轮生成验证 |
| CreateAsset 入库与处理到 Active | 尚未本轮验证 |
| 删除已授权真人素材或组 | 尚未本轮验证，未删除既有库存 |
| API 主动撤回肖像授权 | 未确认对应官方 API，不用删除代替撤权 |

补充只读/非收费探测：官方视频任务列表返回 HTTP 200（RequestId `0217925776104550e23c04e8b740c94d8512f0597aa5fa6a15ff8`，当时0条）；`CreateAssetGroup` 创建临时 AIGC 测试组在写入前即返回 HTTP 403 / `SubscriptionRequired`（RequestId `20261021181453F5EDE8F79A39C5F69D0C`），所以没有产生需要清理的官方测试组。视频列表成功只证明 API Key 和查询端点可用，不证明四个模型均可创建成片。

后续新增实测应追加实际日期、端点、模型、HTTP 状态、上游错误码、RequestId 和最终任务状态。保留失败结果，不以换渠道、只拿到任务 ID 或静态文档代替通过；不要记录真实密钥、认证凭证、H5 链接、素材签名 URL 或私人照片。
