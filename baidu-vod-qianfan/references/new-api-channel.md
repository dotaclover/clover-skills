# new-api 渠道配置

本文使用 new-api 已有渠道类型，不需要为百度 VOD 或 QF 新增渠道类型。先运行真实直连脚本，确认 Base URL、Key 和模型可用，再创建渠道。

## 百度 VOD

- 渠道类型：`OpenAI`（后端 `ChannelTypeOpenAI = 1`）
- 默认 Base URL：`https://vod.bj.baidubce.com/v3/chat/oc`
- Key：VOD API Key 原文，不添加 `Bearer ` 前缀
- 模型：手工填写真实探测通过的模型
- 上游实际路径：`/v1/chat/completions`

VOD 不提供可用的标准模型发现结果，不应把“获取上游模型”失败解释为聊天接口不可用。不要把 Base URL 配成完整的 `/v1/chat/completions` 地址，路径由渠道适配器追加。

## 百度千帆 QF

- 渠道类型：`Baidu V2`（后端 `ChannelTypeBaiduV2 = 46`）
- 默认 Base URL：`https://qianfan.baidubce.com`
- Key：普通 API token；只有需要 appid 时才使用 `token|appid`
- 模型：只启用当前 Key 真实调用通过的模型
- 上游实际路径：`/v2/chat/completions`
- 上游模型目录：`/v1/models`

不要把 `token|appid` 整体作为 Bearer token。渠道适配器应拆分凭据，仅使用 token 鉴权，并在需要的请求中单独携带 appid。

## 百度 AI 网关 Seedance

AI 网关不是聊天渠道，也不是 `Baidu V2` 的 `/v2/chat/completions`。在 new-api 中通过 Seedance 任务插件接入：

- 环境变量参考：`BAIDU_AI_URL=https://ai-gateway.baidubce.com`、`BAIDU_AI_KEY=<AI 网关 Key>`
- 上游创建：`POST {base}/api/v3/contents/generations/tasks`
- 上游查询：`GET {base}/api/v3/contents/generations/tasks/{task_id}`
- 请求使用完整模型名，例如 `doubao-seedance-2-0-260128`、`doubao-seedance-2-5-260628`
- 插件渠道类型：`54` / `45` 走 Ark 原生协议；类型 `46` 走 QF FireSeries
- AI 网关 Key 只放在对应渠道配置中，不下发给网页用户或 API 客户端

客户侧可以继续使用 new-api 对外暴露的统一视频接口；不要让客户直接调用上游 AI 网关，也不要把 AI 网关渠道伪装成聊天渠道。

## 旧 VOD 视频插件

旧 VOD 还存在独立的 V2/V3 视频任务插件能力，和旧 VOD 的 OpenAI 文本渠道不是同一个端点。需要视频时必须按插件文档配置对应的 VOD 凭据和模型限制；新 VOD 不自动继承旧 VOD 的 `/v2` 或 `/v3` 视频路径。

## 客户端验证

渠道配置完成后，使用 new-api 自己签发的 Token 请求统一入口：

```http
POST /v1/chat/completions
Authorization: Bearer <NEW_API_TOKEN>
Content-Type: application/json
```

请求体保持 OpenAI Chat Completions 格式。先使用一个已直连成功的模型发送“你好”，核对 HTTP 状态、响应模型、usage 和渠道日志。上游 Key 只保存在渠道配置中，不提供给客户端。

## 价格

新增内置价格前，读取目标仓库的 billing expression 规范。每个模型使用百度当前官方公布的真实价格，统一换算为 USD/百万 tokens，并分别表达输入、输出及官方明确提供的缓存类别。保留管理员显式价格覆盖；官方未公布或无法核验的价格不得猜测。
