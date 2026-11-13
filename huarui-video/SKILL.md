---
name: huarui-video
description: 华锐视频与合法真人素材接入、核验、查询及生成验收；只操作用户选定并授权的账号/项目，官方Ark协议仅作隔离参考，生成与写操作单独确认。
agent_created: true
---

# Huarui Video

本技能只用于华锐内部视频和当前账号的合法真人素材。支持两条完全隔离的链路：官方火山 Ark，以及华锐网站接口。不得跨链路混用 API Key、IAM AK/SK、任务 ID、素材 ID 或 H5 Token。

## 1. 选定渠道与只读检查

先使用 `api-engineering` 核实当前任务的provider、账号、项目与授权。仅检查用户选定链路，不因已有环境变量自动检查另一渠道，不从其他客户包取凭据。华锐负责人狗总执行本渠道；官方Ark业务交迟空使用 `seedance-dev`。

读取 [references/provider-config.md](references/provider-config.md) 的无密钥配置说明。仅检查变量存在性，不输出值；在授权范围内调用模型与选定素材只读查询。模型列表成功只证明目录可达，不能报告生成或全部素材可用；选定素材必须状态Active且当前账号/项目归属与本人授权有效。

资产ID和真人名称仅保存于仓库外本机私有任务记录，不回写共享技能或Git。按 [references/health-sync.md](references/health-sync.md) 记录检查时间、request_id和脱敏结论；失败保留旧记录标待复核，不猜ID、不自动删除。

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
- 核验结果和新Asset ID写入仓库外本机私有任务记录，不回填共享reference；不得把Group ID当Asset ID。

完整 H5 流程见 [references/h5-liveness.md](references/h5-liveness.md)。

## 3. 生成前的对话确认

生成视频前必须和用户逐项确认以下最终参数；提示词可以在对话中反复完善，未最终确认不得提交任务：

- **接口**：官方 Ark 或华锐；如果用户未指定，展示检查结果并询问选择。
- **真人模特**：是否使用；使用时确认模特名称和对应 Asset ID。没有合法、可用、`Active` 素材时不得声称支持真人模特。
- **模型 ID**：必须确认完整 `model` 字符串，不能只写“2.0”或“2.5”。
- **提示词**：持续根据用户反馈修改，提交前给出最终版。
- **时长**：确认整数秒数，通常为 4–15 秒并以当前模型限制为准。
- **比例、声音、水印、分辨率**：按当前模型能力、素材权利与任务规格逐项确认，不固定两种比例、720p、有声或无水印。

最后一次提交前必须发送一段“最终生成参数”摘要，至少包含 provider、API 地址、模型 ID、模特名称/Asset ID、最终提示词、时长、比例、分辨率、声音及水印设置，并等待用户明确确认。

## 4. 提交、轮询与交付

1. 使用选定 provider 对应的原生 Ark 兼容请求格式，只提交一次；超时先查询任务，不自动重复 POST。
2. 按当前限流设置查询间隔（例如 10 秒）、总等待时限与最大查询次数；达到任一上限停止本地轮询并保存任务 ID，不视为服务端取消，不重提。终态包括 `succeeded`、`failed`、`cancelled` 或 `expired`。
3. 只有状态为 `succeeded` 且存在 `content.video_url` 才报告成功；失败时原样保留真实错误码和错误消息。
4. 成功后先做一次媒体 URL 实际下载/范围校验，再把临时链接交给用户，并提醒及时下载。
5. 报告 provider、API 地址、模型、任务 ID、最终状态和实际规格；不输出 Key、SK、H5 Token 或签名 URL 的调试原文。

## 5. 私有素材记录

不附固定真人名称与素材库存。使用当前用户授权的私有记录，重新核对provider、账号、项目、Group ID、Asset ID、Active状态与授权期限；历史ID不证明当前可用。

提示词引用真人时显式写image 1、image 2并与content顺序一致。素材登记格式见 [references/huarui-account-assets.md](references/huarui-account-assets.md)，官方差异见 [references/ark-account-assets.md](references/ark-account-assets.md)。
