# 百度 Seedance：差异索引，不复制事实源

选择 `provider=baidu` 时，本文件只是跨渠道差异与防误用摘要，不是完整协议。如有变化，以服务方当前文档和有日期的实际证据为准。

## 本包提供什么、缺什么

- 本页已足够识别「百度 ≠ 官方 Ark ≠ 华锐」的关键差异，避免拿错域名、认证或请求格式。
- 逐请求字段明细、RequestId 检索历史、素材 Action 字段大小写、真人 H5 全流程验收，本包不含。
- 本包 `scripts/seedance.py` 仅官方 Ark，不能接百度配置。
- 因此遇到需要完整协议才能推进的环节，先向服务方或使用者取得对应资料后再执行；资料缺失即停止，不凭本页补造参数、不猜测字段。

## 相对官方与华锐的差异

- Base URL 为 `https://ai-gateway.baidubce.com`；环境为 `BAIDU_AI_URL` 和 `BAIDU_AI_KEY`。视频及素材 Action 均使用该百度 Key 的 Bearer，不用 Ark IAM AK/SK，也不使用华锐 Key。
- 视频为 `/api/v3/contents/generations/tasks`，顶层 `content`、整数 `duration`、完整 Seedance 型号；不是华锐 `/v1/videos` 的 `prompt/seconds/metadata` 包装。
- 不把 `/beta/video/generations/qianfan-video/fireseries` 发到 AI 网关；QF 短名 `S2.0/S2.5` 只在事实源指定的类型 46 转换分支使用。
- 素材走同一网关根路径 `/?Action=<Action>&Version=2024-01-01`，JSON 字段大小写按事实源。普通素材、授权素材、项目映射和账号库存不能假设与官方互通。
- H5 创建、真人完成同意、服务端结果查询和素材可用于生成应分别验收。历史创建 H5 成功不证明完整闭环；未扫码查询的真实 404 不改写成 Pending。
- 不把官方 H5 的订阅失败套到百度，也不把百度 H5 成功移作官方证据；有效期字段、回调语义及撤权能力按事实源证据核对。
- 默认仅做静态配置/协议检查。视频收费、素材/H5 外部写、删除及冒烟脚本的写入都须当前用户明确授权；“最小测试”不代表免费或只读。

本次整合不重新联网、不运行百度脚本、不复制百度模块全文或账号库存；协议/历史结果的细节始终回上述文件读取。
