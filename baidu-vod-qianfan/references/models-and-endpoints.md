# 百度四类接入的端点和模型

聊天结果来自 2026-10-12 使用各自真实 Key、消息“你好”的直连测试；AI 网关 Seedance 结果来自 2026-10-16 的最小 5 秒任务提交和查询。模型可用性与账号权限会变化，使用时应重新运行脚本或真实任务验证。

## VOD OpenAI 兼容服务

- Base URL 示例：`https://vod.bj.baidubce.com/v3/chat/oc`
- 聊天端点：`POST {base}/v1/chat/completions`
- 鉴权：`Authorization: Bearer <BAIDU_VOD_KEY>`
- 不需要 `8301` 端口。
- 直接向 Base URL 发 POST 会触发签名格式错误；必须追加聊天端点。
- `/v1/models` 当前不能用于可靠的模型发现，new-api 中应手工配置模型。

已返回 HTTP 200：

- `deepseek-v4-flash`
- `deepseek-v4-pro`
- `glm-5.2`
- `glm-5.3`
- `glm-5.3-flash`
- `kimi-k3`

该次测试未通过：

- `deepseek-v4.1-flash`
- `deepseek-v4-flash-0731`
- `deepseek-v4.1-flash-intl`
- `deepseek-v4-pro-0813-intl`
- `kimi-k2.5`
- `kimi-k2.6`
- `kimi-k2.7-code`
- `kimi-k2.7-code-highspeed`

## 百度智能云千帆 QF

- Base URL 示例：`https://qianfan.baidubce.com`
- 聊天端点：`POST {base}/v2/chat/completions`
- 模型目录：`GET {base}/v1/models`
- 鉴权：`Authorization: Bearer <BAIDU_QF_KEY>`
- 模型目录列出模型不代表当前 Key 已获得调用权限。

已返回 HTTP 200：

- `deepseek-v4-flash-0731`
- `deepseek-v4-pro`
- `deepseek-v4.1-flash`
- `glm-5.2`
- `glm-5.3`

该次测试未通过：

- `deepseek-v4-flash`
- `kimi-k2.5`（模型下线）
- `kimi-k3`
- `kimi-k2.6`

## 请求协议

两类服务均接收 OpenAI Chat Completions 风格的请求体：

```json
{
  "model": "glm-5.3",
  "messages": [
    { "role": "user", "content": "你好" }
  ],
  "max_tokens": 64,
  "stream": false
}
```

VOD 与 QF 的路径不同，不能把同一完整端点用于两个渠道。

## 百度新 VOD

- 环境变量：`BAIDU_NEWVOD_URL`、`BAIDU_NEWVOD_KEY`
- Base URL 示例：`https://vod.gz.baidubce.com`
- 聊天端点：`POST {base}/v1/chat/completions`
- 鉴权：`Authorization: Bearer <BAIDU_NEWVOD_KEY>`
- 不要追加旧 VOD 的 `/v3/chat/oc`。
- 当前 `/v1/models` 不作为可靠发现接口，模型手工配置。

新 VOD 与旧 VOD 的 Key、Base URL 和视频端点都不能互换。

## 百度 AI 网关 Seedance

- 环境变量：`BAIDU_AI_URL`、`BAIDU_AI_KEY`
- Base URL 示例：`https://ai-gateway.baidubce.com`
- 创建任务：`POST {base}/api/v3/contents/generations/tasks`
- 查询任务：`GET {base}/api/v3/contents/generations/tasks/{task_id}`
- 鉴权：`Authorization: Bearer <BAIDU_AI_KEY>`
- 使用完整模型名，不使用 QF 的 `S2.0` / `S2.5` 短名。

已验证模型：

- `doubao-seedance-2-0-260128`
- `doubao-seedance-2-0-fast-260128`
- `doubao-seedance-2-0-mini-260615`
- `doubao-seedance-2-5-260628`

同一 AI 网关如果调用 QF FireSeries 路径 `/beta/video/generations/qianfan-video/fireseries`，会返回 `404 NOT_FOUND`；这属于端点不匹配。

## 图像模型边界

`z-image` 当前只在阿里/Qwen 图像渠道中处理。百度旧 VOD、新 VOD、千帆 QF 和 AI 网关均没有已验证的 `z-image` 文生图实现；不要把该模型加入百度渠道。
