# 百度 Seedance：差异索引，不复制事实源

选择 `provider=baidu` 时，**`baidu-api-dev` 是唯一百度接口事实源**。本文件只是路由与跨渠道防误用摘要；如有变化，以事实源对应模块和有日期的实际证据为准，不在本目录维护另一份完整协议/实测。

## 必须加载的资料

- [Seedance API](../../baidu-api-dev/references/seedance-api.md)：AI 网关原生请求、素材 Action、真人 H5、new-api 路由与 QF 转换。
- [Seedance 实测](../../baidu-api-dev/references/seedance-verification.md)：逐请求 HTTP、RequestId、历史和未验收边界。
- [百度统一入口](../../baidu-api-dev/SKILL.md)：其他百度模块按该入口路由，不把 QF、VOD 与 AI 网关混用。
- CLI 路径：`../../baidu-api-dev/scripts/seedance.py`。先从对应技能目录查看帮助；本技能的 `scripts/seedance.py` 仅官方 Ark，不能接百度配置。

以上是仓库相对路径。单独安装 `seedance-dev.zip` 时需同时取得同级 `baidu-api-dev`；资料缺失则停止百度执行，不凭本索引补造参数。

## 相对官方与华锐的差异

- Base URL 为 `https://ai-gateway.baidubce.com`；环境为 `BAIDU_AI_URL` 和 `BAIDU_AI_KEY`。视频及素材 Action 均使用该百度 Key 的 Bearer，不用 Ark IAM AK/SK，也不使用华锐 Key。
- 视频为 `/api/v3/contents/generations/tasks`，顶层 `content`、整数 `duration`、完整 Seedance 型号；不是华锐 `/v1/videos` 的 `prompt/seconds/metadata` 包装。
- 不把 `/beta/video/generations/qianfan-video/fireseries` 发到 AI 网关；QF 短名 `S2.0/S2.5` 只在事实源指定的类型 46 转换分支使用。
- 素材走同一网关根路径 `/?Action=<Action>&Version=2024-01-01`，JSON 字段大小写按事实源。普通素材、授权素材、项目映射和账号库存不能假设与官方互通。
- H5 创建、真人完成同意、服务端结果查询和素材可用于生成应分别验收。历史创建 H5 成功不证明完整闭环；未扫码查询的真实 404 不改写成 Pending。
- 不把官方 H5 的订阅失败套到百度，也不把百度 H5 成功移作官方证据；有效期字段、回调语义及撤权能力按事实源证据核对。
- 默认仅做静态配置/协议检查。视频收费、素材/H5 外部写、删除及冒烟脚本的写入都须当前用户明确授权；“最小测试”不代表免费或只读。

本次整合不重新联网、不运行百度脚本、不复制百度模块全文或账号库存；协议/历史结果的细节始终回上述文件读取。
