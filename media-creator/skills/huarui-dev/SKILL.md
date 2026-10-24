---
name: huarui-dev
description: 华锐自用开发与接口整合，使用环境变量接入华锐 Ark 兼容和 OpenAI Video 两种协议，覆盖视频任务、素材 Action、状态、错误与授权边界；不代替客户交付包或华锐内部官方真人视频包。
agent_created: true
---

# 华锐自用开发

仅用于自用开发、协议适配和经授权的接口集成。唯一凭据入口是环境变量 `HUARUI_BASE_URL` 与 `HUARUI_API_KEY`；不得读取、复制或内置客户 Key、客户素材 ID、签名链接、内部回调路径或内部自动核对逻辑。

## 使用边界

- 不代替 `huarui-zhisuan` 客户交付包。
- 不代替 `huarui-video` 华锐内部官方真人视频生成包。
- 不默认创建收费视频、真人授权会话或外部写入资源；每次真实请求都要有明确授权。
- 真人、肖像和参考素材必须具有合法使用权限；普通素材入库、素材 `Active` 和真人授权成功是不同状态。
- 不把其他账号、其他平台或组 ID 当作当前账号可引用素材。

## 配置与传输

```dotenv
HUARUI_BASE_URL=https://suanli.huaruiai.com
HUARUI_API_KEY=<仅在本机环境变量或私有配置中设置>
```

始终使用 HTTPS、默认证书校验和 `Authorization: Bearer $HUARUI_API_KEY`。不得跨主机转发 Authorization。`200` 但返回 `text/html` 通常表示协议或路径未进入接口层，不应直接归因于 Key 或余额。

## 最短工作流

1. 显式选择一种视频协议和当前账号可用型号。
2. 检查素材来源、权限、可访问性及是否需要真人授权。
3. 在授权的费用和写入范围内提交一次任务；超时先查询，不自动重复 POST。
4. 使用同一协议、账号和真实任务 ID 轮询到终态。
5. 成功后下载并本地验收；临时签名 URL 不写日志、不共享。

详见 [通用 API 参考](references/api.md)。本技能没有可执行 CLI；请勿把文档示例当成已经存在的命令行工具。