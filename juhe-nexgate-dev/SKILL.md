---
name: juhe-nexgate-dev
description: 开发与排查 Juhe/Nexgate 的 mcwlapi 网关及 mcwlcpa 账号池，覆盖国内/国际版本、渠道协议、图片视频任务、租户计费、本地验证和打包部署。适用于修改这两个项目源码或运行配置；客户调用已部署 API 使用 juhe-nexgate。
metadata:
  version: 1.1.0
  scope: personal-development
---

# Juhe / Nexgate 开发

## 工作区与责任层

- 国内版：`C:/code/mcwlapi`，分支 `dev`；国际版：`C:/code/mcwlapi_internal`，分支 `internal`；账号池：`C:/code/mcwlcpa`。用户提供其他路径时先核实。读取目标仓库 AGENTS、README 与相关实现，检查 git status、分支和已有改动。
- 链路为 `客户端 → mcwlapi → 上游供应商或 mcwlcpa → 授权账号池`。网关负责租户、令牌、路由、额度和日志；CPA 负责授权账号及调度。不要把一层的配置或成功结果当作另一层已经可用。
- 保留 new-api、QuantumNous 身份、许可证、模块路径和来源链接。应用品牌与上游归属并存。
- 共享修改通常先在 dev 实现并提交；用户要求两版时在各自工作树测试、提交，cherry-pick 共享变更。保留币种、充值、导航和部署差异，不直接合并整个分支。
- 区分用户网关令牌、网关到 CPA 的服务 Key、上游 Key/OAuth、CPA 管理 Key。配置只在必要范围内读取，输出脱敏；不将客户凭据、账号授权文件或私有配置复制进技能。

## 按任务加载

| 任务 | 参考 |
| --- | --- |
| 分层架构与责任边界 | [architecture.md](references/architecture.md) |
| 路由、adaptor、租户、计费和前端规约 | [gateway-development.md](references/gateway-development.md) |
| 图片异步、Redis、视频共用记录、恢复 | [async-images.md](references/async-images.md) |
| 百度、阿里、火山协议差异 | [domestic-providers.md](references/domestic-providers.md) |
| CPA 账号池与配置版本 | [account-pool.md](references/account-pool.md) |
| 本地启动、Linux 打包和部署 | [deployment.md](references/deployment.md) |
| 真实验收和故障定位 | [verification.md](references/verification.md) |

## 实施与交付

1. 以当前源码、配置解析器和运行证据为准，参考资料是定位入口。找不到旧路径时搜索函数/路由，不新建重复实现。不把计划、模型列表或本地测试当作公网能力。
2. 明确本次协议、模型映射、渠道、鉴权、计费单位及受影响版本；复用 Router → Controller → Service → Model 和现有 Relay。
3. 在用户授权范围内推进；开发和本地测试请求通常授权必要的本地运行，不重复索要已有许可。真实生成按授权最小数量执行，计费结果不确定时停止重提；不自行扩大为批量压测、账号登录或远程部署。
4. UTF-8 读写，默认真实系统和有限冒烟；按仓库要求补充构建及相关回归。缺依赖明确报告，不用 mock 成功代替真实链路。无要求不创建备份或兼容层。
5. 发布从目标工作树构建；只有用户要求才 push/upload。提交不带 .env、数据库、二进制、图片结果、日志或无关改动。
6. 报告提交、验证环境、实际任务数/费用和未验证边界。技能源是用户指定目录，不擅自同步到个人安装目录、打包或发布客户包。

公开包 `juhe-nexgate` 只记录客户端契约。用户要求同时维护两包时，同步参数、返回值和上线前提，不复制内部主机、数据库名、渠道凭据、测试账号或管理流程。
