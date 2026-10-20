---
name: juhe-nexgate  
description: 调用聚合 Juhe Nexgate API，涵盖 GPT、Claude、DeepSeek、Seedance、Image-2 及当前模型列表中的其他系列。用于获取型号、文本对话与流式输出、Responses、Messages、图片生成与编辑、视频生成与下载，提供参数和 curl 示例。  
agent_created: true  
---

# 聚合 Juhe Nexgate API

通过统一服务地址和 API Key 使用文本、图片和视频接口。根据任务选择对应接口，并从当前 Key 的模型列表中选取完整型号 ID。

## 服务地址与鉴权

| 项目       | 值                                 |
| -------- | --------------------------------- |
| Base URL | `https://juhe.top`                |
| 鉴权       | `Authorization: Bearer <API Key>` |
| JSON 请求头 | `Content-Type: application/json`  |

使用用户提供的 API Key，通过环境变量读取，不把真实 Key 写入文档或示例。下方 curl 使用 Bash 语法。

```bash
export JUHE_BASE_URL='https://juhe.top'
read -rsp 'Juhe API Key: ' JUHE_API_KEY; echo
export JUHE_API_KEY

curl --silent --show-error --fail-with-body \
  "$JUHE_BASE_URL/v1/models" \
  -H "Authorization: Bearer $JUHE_API_KEY"
```

## 按任务选择接口

| 任务与系列                     | 入口                                                    | 调用说明                                                |
| ------------------------- | ----------------------------------------------------- | --------------------------------------------------- |
| GPT、Claude、DeepSeek 等文本对话 | `POST /v1/chat/completions`                           | [文本请求与流式示例](references/text.md)                     |
| GPT Responses             | `POST /v1/responses`                                  | [Responses 示例](references/text.md#3-gpt-responses)  |
| Claude Messages           | `POST /v1/messages`                                   | [Messages 示例](references/text.md#4-claude-messages) |
| Gemini 原生文本请求             | `POST /v1beta/models/{model}:generateContent`         | [Gemini 示例](references/text.md#5-gemini-原生格式)       |
| Image-2 等图片生成与编辑          | `POST /v1/images/generations`、`POST /v1/images/edits` | [图片请求与保存结果](references/images.md)                   |
| Seedance 视频               | 方舟格式或 OpenAI Video 格式                                 | [Seedance 参数与示例](references/seedance.md)            |
| 其他视频型号                    | `POST /v1/videos`                                     | [其他视频请求](references/other-video.md)                 |

型号与请求入口见 [模型清单](references/models.md)，错误原因与处理方法见 [常见报错与处理](references/troubleshooting.md)。型号与可用性会随时间、Key 权限、额度及服务状态变化，以当前 `/v1/models` 和请求响应为准。

## 文本请求快速开始

```bash
curl --silent --show-error --fail-with-body \
  "$JUHE_BASE_URL/v1/chat/completions" \
  -H "Authorization: Bearer $JUHE_API_KEY" \
  -H 'Content-Type: application/json' \
  --data '{
    "model": "gpt-6.1-sol",
    "messages": [{"role": "user", "content": "用三句话介绍太阳能发电。"}],
    "max_tokens": 512,
    "stream": false
  }'
```

文本从 `choices[0].message.content` 读取。调用其他系列时，阅读相应参考文件，按其格式提交。

## 调用要点

- 请求地址使用 `https://juhe.top`；示例中的 `JUHE_BASE_URL` 不包含 `/v1`，按示例拼接路径。
- `GET /v1/models` 返回的 `data[].id` 是请求所用的型号名称；按文本、图片、视频任务选用对应接口。
- 文本流式请求读取 SSE；图片响应可能是 Base64 或 URL；视频创建返回任务 ID，须查询到完成后下载。
- 视频两种创建格式任选一种，同一需求只提交一次。超时或暂时查询失败时，先核对已有任务。
- 发生错误时读取响应中的 `error`。`401` 检查 Key，`400` 检查参数，`403` 检查权限，`429` 根据具体错误区分限流与额度问题；`5xx` 或超时保留错误信息后再处理。
- 图片、视频等长耗时任务必须显式设超时：图片 `--max-time 180`–`300`，视频创建后用任务 ID 轮询。不要依赖默认无限等待。
- `/v1/models` 能列出型号不代表该型号当前可用。某型号超时或返回 `524` 时，先用文本型号发一条最小请求探活，再换同系列型号验证，不要持续加大等待时间；判定流程见 [常见报错与处理](references/troubleshooting.md)。
