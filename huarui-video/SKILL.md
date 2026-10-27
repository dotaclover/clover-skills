---
name: huarui-video
description: 华锐内部真人视频生成与官方 Ark 账号资源管理；自动检查两套接口、同步官方资产、创建并核验华锐 H5 真人授权，生成前必须完成参数确认。
---

# Huarui Video

本技能只用于华锐内部视频和当前账号的合法真人素材。支持两条完全隔离的链路：官方火山 Ark，以及华锐网站接口。不得跨链路混用 API Key、IAM AK/SK、任务 ID、素材 ID 或 H5 Token。

## 1. 启动检查与自动同步

每次进入本技能，先执行检查，不直接假设上次状态仍有效。

### 官方 Ark

1. 检查当前进程是否同时配置 `ARK_KEY`、`ARK_ACCESS_KEY`、`ARK_SECRET_KEY`。
2. 三项齐全时，用 `ARK_KEY` 请求官方视频 API 做连通性检查；用 `ARK_ACCESS_KEY` + `ARK_SECRET_KEY` 对官方素材 Action 做 HMAC V4 鉴权检查。
3. 官方视频和素材都成功时，立即同步官方资产：使用 REF 中已知组 ID，或使用用户提供的网页资产组结果，再调用 `ListAuthorizedFirstAssetByGroups`（`Version=2024-01-01`）查询每组真实的 `Active` Asset ID。网页侧的 `ListActiveAuthorizationAssetGroup`（`Version=2024-10-01`）不是当前公开 HMAC Action，不能把它当作原始 API 必然可调用。
4. 只把真实返回的组名、Group ID、Asset ID、状态、项目和有效期写入 [references/ark-account-assets.md](references/ark-account-assets.md)，并同步本文件的素材表。同步失败时保留旧记录并明确报告，不猜 ID。

### 华锐

1. 使用 [references/provider-config.md](references/provider-config.md) 中的华锐 API URL 和内置 Key 检查视频接口连通性；没有官方变量也可以执行。
2. 连通后检查素材接口：查询 `LivenessFace` 组、组内素材和每个已登记素材的状态。只有请求成功且素材为 `Active` 才报告“可用”；`Processing`、空列表、单个资源失败都不能报告全部可用。
3. 将华锐侧实际查询到的素材状态写入 [references/huarui-account-assets.md](references/huarui-account-assets.md)。华锐资源和官方 Ark 资源分开记录。

详细地址、请求体、环境变量、脱敏和停止条件见 [references/provider-config.md](references/provider-config.md) 与 [references/health-sync.md](references/health-sync.md)。

## 2. 华锐 H5 真人模特

用户要求生成真人模特链接时，使用华锐接口的 `CreateVisualValidateSession`：

1. 使用同一个华锐 API URL、Bearer Key 和 `ProjectName`。
2. 默认不填写 `CallbackURL`，除非用户提供受控的公网 HTTPS 回调地址。
3. 返回 `H5Link` 后只展示给真人授权人本人；`BytedToken` 只保存于当前私有流程，不写日志、REF 或 Git。
4. H5 链接打开不等于核验成功，必须等待真人本人完成授权。

真人完成后，使用同一个华锐 Key 和原始 `BytedToken` 调用 `GetVisualValidateResult`：

- 成功标准：`ResultCode=10000` 且返回 `GroupId`。
- 成功后按该 `GroupId` 查询 `LivenessFace` 素材组，等待素材状态为 `Active`。
- 未完成、`404 token not found`、上游失败、通知内容或浏览器回跳都不能当作核验成功。
- 核验结果和新 Asset ID 写入 [references/huarui-account-assets.md](references/huarui-account-assets.md)，不得把 Group ID 当 Asset ID。

完整 H5 流程见 [references/h5-liveness.md](references/h5-liveness.md)。

## 3. 生成前的对话确认

生成视频前必须和用户逐项确认以下最终参数；提示词可以在对话中反复完善，未最终确认不得提交任务：

- **接口**：官方 Ark 或华锐；如果用户未指定，展示检查结果并询问选择。
- **真人模特**：是否使用；使用时确认模特名称和对应 Asset ID。没有合法、可用、`Active` 素材时不得声称支持真人模特。
- **模型 ID**：必须确认完整 `model` 字符串，不能只写“2.0”或“2.5”。
- **提示词**：持续根据用户反馈修改，提交前给出最终版。
- **时长**：确认整数秒数，通常为 4–15 秒并以当前模型限制为准。
- **比例**：只接受 `9:16` 或 `16:9`。
- **声音**：默认 `generate_audio=true`。
- **水印**：默认 `watermark=false`。
- **分辨率**：默认 `720p`，如接口或用户要求不同则单独确认。

最后一次提交前必须发送一段“最终生成参数”摘要，至少包含 provider、API 地址、模型 ID、模特名称/Asset ID、最终提示词、时长、比例、分辨率、有声和无水印，并等待用户明确确认。

## 4. 提交、轮询与交付

1. 使用选定 provider 对应的原生 Ark 兼容请求格式，只提交一次；超时先查询任务，不自动重复 POST。
2. 每 10 秒查询任务，直到 `succeeded`、`failed`、`cancelled` 或 `expired`。
3. 只有状态为 `succeeded` 且存在 `content.video_url` 才报告成功；失败时原样保留真实错误码和错误消息。
4. 成功后先做一次媒体 URL 实际下载/范围校验，再把临时链接交给用户，并提醒及时下载。
5. 报告 provider、API 地址、模型、任务 ID、最终状态和实际规格；不输出 Key、SK、H5 Token 或签名 URL 的调试原文。

## 5. 现有真人素材索引

该表只作为当前已知索引；每次官方同步或华锐素材检查后，以对应 REF 的真实查询结果为准。

| 名称 | Asset ID | 引用 |
|---|---|---|
| 林冯（组 95tcv） | `asset-20261013113659-4jz89` | `asset://asset-20261013113659-4jz89` |
| 缪志翔 | `asset-20261013113532-s2q8c` | `asset://asset-20261013113532-s2q8c` |
| 林冯（组 lp5rb） | `asset-20261013114040-jspbc` | `asset://asset-20261013114040-jspbc` |
| 林冯1 | `asset-20261013114340-2gqft` | `asset://asset-20261013114340-2gqft` |

提示词引用真人时必须显式写 `image 1`、`image 2` 等，并与 `content` 中图片顺序一致。只使用当前 provider、当前项目和当前授权关系下的真实 Asset ID。
