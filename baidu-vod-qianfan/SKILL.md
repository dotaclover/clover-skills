---
name: baidu-vod-qianfan
description: 真实探测并配置 new-api 的百度渠道：旧 VOD、新 VOD、千帆 QF，以及 AI 网关 Seedance。用于核对 Base URL、API Key、模型权限、OpenAI Chat Completions、Seedance 原生任务端点、渠道类型和模型映射；不把四套服务的 Key 或端点混用。
agent_created: true
---

# 百度渠道与 Seedance

先读取 new-api 实际渠道实现和当前项目文档，再直连真实上游，最后配置 new-api。不得用 mock、备用供应商或伪造响应掩盖缺少配置、权限不足、模型下线或端点错误。

## 四种接入先分清

| 接入 | new-api 用途 | 主要上游端点 | 渠道/任务类型 |
|---|---|---|---|
| 旧 VOD | OpenAI 兼容聊天；另有旧 VOD 视频任务插件 | `{BAIDU_VOD_URL}/v1/chat/completions` | OpenAI；视频使用 Baidu VOD task plugin |
| 新 VOD | OpenAI 兼容聊天 | `{BAIDU_NEWVOD_URL}/v1/chat/completions` | OpenAI |
| 千帆 QF | 千帆聊天；Seedance FireSeries 视频 | `{BAIDU_QF_URL}/v2/chat/completions`；视频 `/beta/video/generations/qianfan-video/fireseries` | Baidu V2 `46`；Seedance plugin 也支持 `46` |
| AI 网关 | 火山方舟兼容 Seedance 原生视频 | `{BAIDU_AI_URL}/api/v3/contents/generations/tasks` | Seedance task plugin，直发 Ark 原生协议 |

旧 VOD、新 VOD、QF 和 AI 网关必须分别配置 Base URL 与 Key。Key 不互换；AI 网关不能使用千帆 FireSeries 路径。

## 真实探测

从当前进程环境读取以下变量，不把 Key 写入命令、代码、文档或输出：

- `BAIDU_VOD_URL`、`BAIDU_VOD_KEY`
- `BAIDU_NEWVOD_URL`、`BAIDU_NEWVOD_KEY`
- `BAIDU_QF_URL`、`BAIDU_QF_KEY`
- `BAIDU_AI_URL`、`BAIDU_AI_KEY`

运行：

```powershell
& .\scripts\test-baidu-provider.ps1
```

脚本使用“你好”逐个测试旧 VOD、 新 VOD 和千帆聊天模型，输出供应商、模型、HTTP 状态、耗时及回复或上游错误。任一所选供应商缺配置、传输失败或返回非 2xx 时，脚本以非零状态退出。可用 `-Provider Vod`、`-Provider NewVod` 或 `-Provider Qianfan` 只测试一个供应商，也可用模型参数指定测试矩阵。

AI 网关 Seedance 是异步视频任务，不能用聊天脚本代替。真实生成会产生费用；只有用户明确要求真实生成测试时，才使用 [references/seedance-ai-gateway.md](references/seedance-ai-gateway.md) 中的最小 5 秒请求，并记录任务 ID、HTTP 状态和轮询状态，不记录 Key 或签名视频 URL。

不要根据模型目录判断当前 Key 一定有权限。模型目录、已实测模型和端点差异见 [references/models-and-endpoints.md](references/models-and-endpoints.md)。

## 接入 new-api

直连成功后，读取 [references/new-api-channel.md](references/new-api-channel.md)，按供应商创建独立渠道。不要让旧 VOD、新 VOD、QF 和 AI 网关共用 Base URL、端点拼接或 Key。

新建或修改渠道代码时保持以下协议边界：

- VOD Base URL 后追加 `/v1/chat/completions`。
- 新 VOD Base URL 后追加 `/v1/chat/completions`，不要套用旧 VOD 的 `/v3/chat/oc`。
- QF Base URL 后追加 `/v2/chat/completions`。
- VOD、新 VOD 和 QF 聊天请求都使用 `Authorization: Bearer <key>`。
- VOD 不支持可靠的 `/v1/models` 发现，模型必须手工配置。
- 新 VOD 当前也不要依赖 `/v1/models`；模型手工配置。
- QF 的 `token|appid` 只在需要 appid 时使用；适配器必须拆分 token 和 appid，不能把复合值整体放入 Bearer。
- AI 网关 Seedance 使用完整模型名和 `/api/v3/contents/generations/tasks`；不要映射成 QF 的 `S2.0`、`S2.5` 短名。
- 只有真实直连成功的模型才可加入渠道模型列表。

Seedance 插件的渠道类型边界和媒体角色转换见 [references/seedance-ai-gateway.md](references/seedance-ai-gateway.md)。

## `z-image` 边界

`z-image` 当前由 `relay/channel/ali` 的阿里/Qwen 图像渠道处理。百度 V2 图像转换仍未实现；旧 VOD、新 VOD、QF 和 AI 网关都不能宣称支持 `z-image` 文生图。不要把 `z-image` 填入百度渠道。

新增内置价格时以供应商当前官方价格页为唯一事实来源，记录币种、计价单位、输入/输出及缓存分类；按目标 new-api 仓库的 billing expression 规则写入，不猜价，也不把模型比率当作官方单价。
