# CloverAPI 内部开发总览

适用项目：`C:\code\cloverapi`。本文只记录源码和项目文档能够支持的结论，不包含密钥、真实任务 ID、签名媒体 URL、客户库存或内部私密回调。

## 1. 当前结论

| 范围 | 当前结论 | 证据位置 | 状态边界 |
|---|---|---|---|
| 百度 AI Gateway | 作为 Seedance Ark 兼容上游使用，地址为 `https://ai-gateway.baidubce.com` | `docs/BAIDU_INTEGRATION_SUMMARY.md`、`plugins/tasks/doubao/plugin.js`、`extensions/seedanceapi/` | 有历史测试记录；本次未重发上游请求 |
| Seedance 视频 | 通过 `doubao` 任务插件统一分发，支持 Ark、OpenAI Video 及千帆转换链路 | `docs/clover/video-api-internal.md`、`router/video-router.go` | 源码和已有验证记录已核对 |
| Seedance 工作台 | 已有创作、任务列表、上传、模特授权等页面/接口 | `extensions/studio/`、`web/src/routes/_authenticated/video/seedance/` | 本地功能有多项验证；公网和真实付费闭环仍待验收 |
| 素材隔离 | 资源绑定到用户、渠道、项目；不直接暴露共享上游库存 | `model/seedance_api_resource.go`、`extensions/seedanceapi/routes.go` | 代码静态核实，历史测试记录支持 |
| Codex OAuth | 已有刷新 Token、更新 Codex 渠道凭据、提取账号和邮箱信息 | `service/codex_oauth.go`、`service/codex_credential_refresh.go` | 是上游授权基础，不等于完整 GPT 登录产品 |
| 平台 OAuth | 已有登录、绑定、验证和通用自定义 Provider 机制 | `controller/oauth.go`、`oauth/registry.go` | 平台身份链路与模型授权链路分开 |

## 2. 百度 AI Gateway 与模型

百度接入至少要区分旧 VOD、新 VOD、千帆 QF 和 AI Gateway，不能共用地址或凭证。AI Gateway 的 Seedance 请求为：

```text
POST /api/v3/contents/generations/tasks
GET  /api/v3/contents/generations/tasks/<task_id>
```

客户请求先进入网关，再由 `doubao` 任务插件按渠道类型和模型分发。AI Gateway 走 Ark 原生请求；千帆渠道走 FireSeries，不应把两种路径混用。

项目既有记录中出现并测试过的文本模型包括 `glm-5.3`、`kimi-k3`、`deepseek-*` 等，但这些记录依赖特定账号和历史时点。维护时必须以当前渠道模型、分组、权限和真实请求结果为准。

## 3. “隐藏使用 Seedance”的准确表述

目前可以确认：

- 浏览器工作台不接触上游 API Key。
- 网页请求进入 `/pg/studio/seedance/generations`，复用登录会话、官方任务插件、渠道分发和账务。
- 工作台通过模型列表接口展示当前分组可用模型，不把上游账号库存直接暴露给用户。
- 百度 AI Gateway、火山 Ark 和千帆由服务端渠道配置区分，用户不需要直接感知上游协议差异。

因此，“隐藏”应理解为服务端封装和凭据隔离，不应理解为绕过用户授权、绕过上游权限或伪造模型能力。

## 4. 现有代码入口

- 视频路由：`router/video-router.go`、`router/task-plugin-protocol-router.go`
- Seedance 任务插件：`plugins/tasks/doubao/plugin.js`
- 工作台后端：`extensions/studio/routes.go`、`extensions/studio/seedance/`
- 工作台前端：`web/src/routes/_authenticated/video/seedance/`、`web/src/features/studio/seedance/`
- 百度/Seedance 资产 API：`extensions/seedanceapi/routes.go`、`extensions/seedanceapi/provider.go`
- 资源归属：`model/seedance_api_resource.go`、`model/studio_ark_asset.go`
- 清理配置：`setting/seedance_setting/config.go`

## 5. 待完善顺序

1. 对当前实际渠道逐模型确认 `glm-5.3`、`kimi-k3`、`deepseek` 的真实模型 ID、权限和分组，不把目录存在当成可调用。
2. 完成 Seedance 工作台公网 HTTPS 回跳、真实渠道生成、终态成片、计费/退款和部署版本验收。
3. 对真人授权单独做人工同意到资源绑定再到成片的闭环验收，不用普通素材 CRUD 代替。
4. 继续定位“隐藏使用 Seedance”是否有特定产品入口、默认模型或后台自动路由规则；确认后再写成固定行为。
5. 在 GPT OAuth 之前先定义账号对象、刷新/失效、并发锁、撤销、隐私存储和审计边界。
