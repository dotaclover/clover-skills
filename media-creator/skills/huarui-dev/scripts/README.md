# 脚本说明

`huarui-dev` 当前不是可执行 CLI，而是 `C:\code\cloverapi` 的内部开发记录入口。

本技能不自动发起百度、Seedance、真人授权或 OAuth 请求，不读取客户包凭据，也不执行部署。需要实现或验证功能时，应直接在 `C:\code\cloverapi` 的受控开发环境中按项目文档操作，并单独记录运行验证结果。

主要导航：

- `../references/cloverapi.md`：功能状态、代码入口和待完善路线。
- `../references/studio.md`：Seedance 工作台调用链与验收边界。
- `../references/oauth.md`：GPT/Codex 与平台/WorkBuddy OAuth 的区分。
- `../references/api.md`：历史华锐通用协议参考，仅在明确处理华锐兼容接口时使用。
