# 百度 / 阿里 / 火山渠道差异

以下来自本地 mcwlapi 源码，不代表供应商最新公开承诺。实际可用模型、账号授权、地区与价格按当前账户确认。默认 URL 取自 `constant/channel.go`，不包含任何生产配置。

## 渠道选择表

| 供应商 | 类型 | 默认 Base URL | 主要 adaptor |
|---|---|---|---|
| 百度旧版文心 | 15 / Baidu | `https://aip.baidubce.com` | `relay/channel/baidu/` |
| 百度千帆 V2 | 46 / BaiduV2 | `https://qianfan.baidubce.com` | `relay/channel/baidu_v2/` |
| 阿里 DashScope | 17 / Ali | `https://dashscope.aliyuncs.com` | `relay/channel/ali/` |
| 火山 Ark | 45 / VolcEngine | `https://ark.cn-beijing.volces.com` | `relay/channel/volcengine/` |
| 豆包视频 | 54 / DoubaoVideo | `https://ark.cn-beijing.volces.com` | `relay/channel/task/doubao/` |

## 百度

### 旧版 15

- 请求拼接 `/rpc/2.0/ai_custom/v1/wenxinworkshop/{suffix}`；模型决定 chat/embedding 子路径。
- adaptor 从渠道 Key 获取 access token，并将其写入查询参数；不能套用 V2 的 Bearer-only 假设。
- 账号参数格式继续读取 `relay/channel/baidu/relay-baidu.go` 中 token 获取实现；不要猜测所有百度凭据通用。
- 当前适配中存在未实现的 Responses、Claude 等转换；不要因网关暴露接口就声明该渠道支持。

### 千帆 46

- 普通接口使用 `/v2/chat/completions`、`/v2/embeddings`、`/v2/images/generations`、`/v2/images/edits`、`/v2/rerank`。
- 普通 adaptor 将渠道 Key 按 `|` 拆分：第一段作为 Bearer，存在第二段时作为 `appid`。不要把分隔格式误用到其他供应商。
- 百度视频复用 `task/doubao`，但创建路径是 `/v2/mm/fire/generations/tasks`，查询在其后追加 task_id。
- 视频 task adaptor 使用渠道 Key 设置 Bearer；普通文本的 `token|appid` 拆分逻辑不能推定在视频中同样生效。文本/视频需要分别验证，必要时拆分渠道。
- 视频内部具有 Fire 模型映射、参考视频转换、未解析素材清理和任务状态转换；修改前读取 `relay/channel/task/doubao/adaptor.go` 与测试。

## 阿里 17

- Chat 使用 `/compatible-mode/v1/chat/completions`，embedding 使用 `/compatible-mode/v1/embeddings`。
- Responses 使用 `/api/v2/apps/protocols/compatible-mode/v1/responses`。
- 部分模型可走 `/apps/anthropic/v1/messages`；选择受 `ALI_ANTHROPIC_MESSAGES_MODELS` 与当前 adaptor 判断影响，不代表所有阿里模型具有 Claude 的全部能力。
- 鉴权为 `Authorization: Bearer <供应商Key>`；流式可能带 `X-DashScope-SSE: enable`。
- 视频 task adaptor 位于 `relay/channel/task/ali/`：创建 `/api/v1/services/aigc/video-generation/video-synthesis`，查询 `/api/v1/tasks/{task_id}`，异步头为 `X-DashScope-Async: enable`。
- 阿里请求采用 `model + input + parameters` 等结构，不能简单改 URL 后发送 Ark 原生视频 body。

## 火山 45 / 54

- 45 的文本路径包括 `/api/v3/chat/completions`、`/api/v3/embeddings`、`/api/v3/responses`；部分 bot 模式使用 `/api/v3/bots/chat/completions`。
- 文本/视频通常使用 Bearer Key；特殊语音协议另行核实，不套用到本指南的文本视频链路。
- 视频 45 和 54 均通过 `task/doubao`，创建 `/api/v3/contents/generations/tasks`，查询追加 task_id。
- 上游模型可能要求具体模型 ID 或已开通的推理接入点；从当前账号/配置确认后设置映射，不硬编码猜测。
- 百度 Fire 与 Ark 即便复用同一 Go adaptor，也仍属于不同协议、凭据、模型和计费来源。

## 接入顺序

1. 记录供应商、渠道类型、协议、上游模型标识和授权范围。
2. 通过源码确定 Base URL 拼接和鉴权；避免重复版本路径。
3. 创建单渠道、单模型、限定分组的测试配置。
4. 授权后执行一次最小非流式请求，再分别验收流式、工具或视频任务。
5. 核对 usage、结算与错误转换后，才放开正式分组。
6. 如需新增 adaptor，覆盖路径、鉴权、模型映射、流式、错误、usage 与退款测试，不仅覆盖成功响应。

## 与已有技能协作

百度专有接口细节继续以 `baidu-api-dev` 为独立资料源；Seedance 跨 provider 用法可参考仓库 `seedance-dev`。不要把其他技能、客户包的真实 Key、素材 ID 或签名链接复制到开发指南。缺少相邻技能时直接读当前代码，本技能仍可独立定位开发入口。
