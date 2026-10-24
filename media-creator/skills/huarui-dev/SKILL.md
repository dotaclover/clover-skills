---
name: huarui-dev
description: CloverAPI 内部开发记录与维护导航，覆盖百度 AI Gateway、Seedance 隐藏调用、Seedance 工作台、模型接入和 OAuth 路线；不作为对外接口包或客户交付包。
agent_created: true
---

# CloverAPI 内部开发

本技能是 `C:\code\cloverapi` 的自用开发知识库入口，用于记录已经实现、静态核实、待完善和未来探索的功能。它不是华锐远程 API 调用教程，也不代替客户交付包。

## 边界

- 只记录和维护 `C:\code\cloverapi` 内部实现；不读取或复制客户 Key、客户素材库存、签名链接和内部私密回调。
- 不代替 `huarui-zhisuan` 客户交付包，也不代替 `huarui-video` 内部官方真人视频包。
- 不因文档、文件名或模型目录存在，就宣称功能已上线或完成真实上游验收。
- 真实视频、真人授权和 OAuth 联调都必须有明确授权、费用边界和合法账号；本技能默认只做代码分析和维护规划。

## 当前功能地图

### 已由项目文档和源码静态核实

- **百度 AI Gateway**：百度渠道可作为 Seedance 上游，Base URL 为 `https://ai-gateway.baidubce.com`；统一复用 `doubao` 任务插件，走 Ark 内容生成任务协议，而不是千帆 FireSeries。
- **Seedance 视频链路**：公开入口包含 OpenAI Video 兼容接口、Ark 原生接口和旧兼容入口；任务经过模型/渠道分发、持久化、后台轮询、预扣与完成结算。
- **Seedance 工作台**：已有视频创作、任务列表、素材上传和真人/模特授权相关页面与接口，网页复用登录会话、官方任务插件和账务，不让浏览器接触上游 Key。
- **素材与授权隔离**：`extensions/seedanceapi`、`model/seedance_api_resource.go` 等实现了用户、渠道、项目和资源归属校验；授权 Token 以摘要定位、密文保存，并有失效清理配置。
- **Codex/GPT OAuth 基础**：项目已有 Codex OAuth 刷新、JWT 信息提取、Codex 渠道凭据更新，以及平台 OAuth 登录/绑定和可配置通用 OAuth Provider。它们分别属于上游账号授权和平台身份登录，不能混为一个“GPT 登录”功能。

### 用户已提出、但仍需继续完善或核实

- `glm5.3`、`kimi-k3`、`deepsek`：项目资料中出现过 `glm-5.3`、`kimi-k3`、`deepseek` 等名称，但实际可用模型 ID、渠道权限、模型路由和用户分组仍需按当前配置确认；不得把口语 `deepsek` 直接写成已确认的供应商模型名。
- Seedance 工作台：基础功能已存在，仍需按实际优先级补齐真实渠道生成、最终状态/扣费对账、浏览器公网回跳、真人授权到成片以及发布环境验收。
- 隐藏使用 Seedance：当前可核实的是工作台不暴露上游 Key，并通过统一 `doubao` 插件和渠道能力调用；若“隐藏”还包含特定产品入口、默认模型或后台路由规则，应继续定位对应业务代码后再补文档。
- GPT OAuth：已有 Codex OAuth 刷新基础，但尚未据此宣称已完成面向用户的 GPT OAuth 登录、账号池管理或完整授权页面。
- `workbuyy oauth`：按用户原文保留为未来探索项；若指 WorkBuddy OAuth，需要先确认目标是 WorkBuddy 身份登录、上游模型授权，还是两者之间的账号绑定，再核对正式协议和回调能力。

## 维护入口

- 总览与状态：`references/cloverapi.md`
- 百度与 Seedance 事实记录：`references/baidu-seedance.md`
- Seedance 工作台内部调用链：`references/studio.md`
- OAuth 区分与路线：`references/oauth.md`
- 旧华锐协议文档：不再作为本技能主定位；如需追溯，仅在明确指定时查看 `references/api.md`。

## 工作纪律

1. 先区分“用户确认”“代码静态核实”“已有历史测试”“待完善”“未执行验证”。
2. 先读 `C:\code\cloverapi` 的源码和项目文档，再更新本技能；不凭文件名补全功能。
3. 不启动收费生成、不创建真人授权、不部署、不修改 `cloverapi` 业务代码，除非用户另行明确要求。
4. 不回显或写入任何 Key、Token、签名 URL、私人素材 ID 和账号库存。
5. 修改完成后只校验技能目录、引用和文档一致性；业务运行验证需单独说明。
