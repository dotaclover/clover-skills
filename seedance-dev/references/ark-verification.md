# 官方直连复验与证据边界

本文件将历史账号复测经验转为中性复验步骤，不是当前账号的验证结论。真实账号库存、余额、订阅状态、RequestId 与本机配置修复记录仅保存在当前任务授权的私有证据目录；不回写共享技能。公开官方域名、Action、认证与错误语义保留如下。

## 1. 已有控制台真人素材查询

```http
POST https://ark.cn-beijing.volcengineapi.com/?Action=ListAuthorizedFirstAssetByGroups&Version=2024-01-01
```

1. 确认当前账号/项目及只读授权。素材使用 IAM AK/SK、HMAC V4，Region `cn-beijing`、Service `ark`，不能以视频 Bearer Key 代替 IAM 凭据。
2. 从授权人提供的私有记录取得实际 GroupId，按接口要求传 `Statuses: ["Active", "Processing"]` 和当前 `ProjectName`；`default` 仅为协议默认项目，不是所有任务的项目。
3. 保存 HTTP、`ResponseMetadata`、Action/Version/Service/Region、RequestId、返回素材类型、状态和项目到私有证据目录。不得预填成功数量或 Active 状态。
4. 如需比较普通 `ListAssetGroups` 的真人过滤查询，单独记录其结果。历史中性案例曾出现该查询 HTTP 200 空列表，而已知组查询返回 Active 素材；两类查询不能互相替代，空列表不能证明没有已授权素材。

`ListAuthorizedFirstAssetByGroups` 依赖已知组 ID，每组返回首个符合条件的素材；不能据此宣称自动发现所有组或返回组内全部素材。查询成功只证明该次账号/项目的选定资源可查，不证明可生成视频。

## 2. API 创建新的 H5 真人认证

```http
POST https://ark.cn-beijing.volcengineapi.com/?Action=CreateVisualValidateSession&Version=2024-01-01
```

创建会话属于外部写操作，先确认权限、额度与用户授权，不用于默认探活。标准请求按当前协议传 `CallbackURL` 和 `ProjectName`，不擅自添加未经确认的期限字段。

历史中性案例：请求返回 HTTP 403、`SubscriptionRequired`，消息为 `This API requires an active subscription. Please subscribe to an advanced or premium plan.`。该错误只说明当次请求被订阅条件拦截，不代表当前账号必定受限，也不代表所有素材查询均无权限。

若包含 `authorization.valid_days` 或错误字段类型的请求先被订阅条件拦截，不能判定该字段被支持、忽略或不合法；不能将失败归因为“必须删掉期限参数”。不为验证未知字段自动创建会话。当前公开字段依据与服务方说明不足时标未确认。

没有成功返回当前官方会话及真人本人完成核验的证据，不报告官方 H5 闭环成功。

## 3. 历史成功记录的渠道边界

复核每条证据的 provider、实际请求域名、认证方式、账号/项目与响应。第三方兼容渠道 H5 成功不能作为官方直连成功证据；缺乏渠道信息的旧报告标来源待核验，不推断全部来自官方或第三方。H5 可打开不证明真人已同意、上游结果可查或素材已绑定。

## 4. 当前任务验收表

按当前任务逐项填写“通过/失败/未验证/不适用”，默认不继承历史账号结果：

| 能力 | 所需证据与边界 |
|---|---|
| 官方 API 新建 H5 | 获准的创建响应与真实错误；订阅失败不能记成功 |
| 真人本人同意、回跳和绑定 | 本人操作及主动结果查询，网页成功码不能替代 |
| API 设置肖像授权起止时间 / `valid_days` | 当前公开字段或服务方契约；不从控制台能力推断 |
| 候选模型逐项生成 | 每个型号独立的创建与终态证据；模型可见不等于生成成功 |
| 已有真人素材用于生成视频 | 当前合法授权、Active 与实际生成证据分别核验 |
| CreateAsset 入库到 Active | 创建获准、真实状态处理完成 |
| 删除素材或组 | 单独授权且限定资源，未执行标未验证 |
| 主动撤回肖像授权 | 确认专用官方 API，不用删除代替撤权 |

视频任务列表 HTTP 200 只证明当次 API Key 和查询端点可用，不证明型号均能创建成片。`CreateAssetGroup` 即使拟建临时 AIGC 组也属外部写入，不能因称为免费测试而默认执行。若写入前返回 `SubscriptionRequired`，保存失败，不虚构创建结果或清理任务。

## 5. 凭据排错与私有证据入口

1. 显式确认当前任务凭据来源，仅检查变量存在性和必要格式，不回显值、不扫描其他项目配置。素材变量为 `ARK_ASSET_ACCESS_KEY` / `ARK_ASSET_SECRET_KEY`，视频为 `ARK_API_KEY`；IAM Access Key 的格式检查不能代替签名验证。
2. 使用已授权只读 Action 区分签名/鉴权错误与业务订阅错误。正常 `ResponseMetadata` 和只读成功不意味着写权限有效，修复本机配置也不意味着账号订阅已变化。
3. 复验同一资源时保留当前时间、provider、项目、Action/Version、HTTP、错误码、RequestId、状态及私有证据路径。状态变化按本次真实返回记录，不以旧素材数量或过去成功次数作为默认值。
4. 新建 H5 未获成功时，不编造 BytedToken 或继续伪造结果查询。生成、创建、更新和删除另行授权，不以换渠道或只拿到任务 ID 替代验收。

私有记录至少包含任务标识、配置来源（不含值）、检查日期、端点、型号、HTTP、上游错误码、RequestId、最终状态、证据文件位置和未验证项。共享报告仅给脱敏结论；真实密钥、认证凭证、H5 链接、签名素材 URL 与私人照片不进入共享文档。
