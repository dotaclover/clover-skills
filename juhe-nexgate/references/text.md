# 文本接口：GPT、Claude、DeepSeek 与其他系列

先设置 SKILL.md 中的 `JUHE_BASE_URL` 和 `JUHE_API_KEY`。当前完整型号见 [模型清单](models.md)。

## 1. Chat Completions

GPT、Claude、DeepSeek，以及模型清单中的 Gemini、GLM、Kimi、Qwen 文本型号，均可使用 `POST /v1/chat/completions`。

| 字段 | 类型 | 说明 |
|---|---|---|
| `model` | string，必填 | 当前 Key 可用的完整型号 ID |
| `messages` | array，必填 | 对话消息；每条包含 `role` 与 `content` |
| `max_tokens` | integer | 输出 token 上限；示例为 `512`，按所需输出长度调整 |
| `stream` | boolean | `false` 返回 JSON，`true` 返回 SSE |

GPT 示例见 SKILL.md；Claude 和 DeepSeek 可按下方请求，也可替换为模型清单中的同系列完整型号。

```bash
curl --silent --show-error --fail-with-body \
  "$JUHE_BASE_URL/v1/chat/completions" \
  -H "Authorization: Bearer $JUHE_API_KEY" \
  -H 'Content-Type: application/json' \
  --data '{
    "model": "claude-opus-4-8",
    "messages": [{"role": "user", "content": "用三句话解释什么是缓存。"}],
    "max_tokens": 512,
    "stream": false
  }'
```

```bash
curl --silent --show-error --fail-with-body \
  "$JUHE_BASE_URL/v1/chat/completions" \
  -H "Authorization: Bearer $JUHE_API_KEY" \
  -H 'Content-Type: application/json' \
  --data '{
    "model": "deepseek-v4.1-flash",
    "messages": [{"role": "user", "content": "请给出一个 Python 列表去重示例。"}],
    "max_tokens": 512,
    "stream": false
  }'
```

回复位于 `choices[0].message.content`，用量位于 `usage`。多轮对话按时间顺序传入之前的 `user` 与 `assistant` 消息。

## 2. Chat Completions 流式输出

```bash
curl --silent --show-error --fail-with-body --no-buffer \
  "$JUHE_BASE_URL/v1/chat/completions" \
  -H "Authorization: Bearer $JUHE_API_KEY" \
  -H 'Content-Type: application/json' \
  --data '{
    "model": "gpt-6.1-sol",
    "messages": [{"role": "user", "content": "简要介绍三个提高工作效率的方法。"}],
    "max_tokens": 256,
    "stream": true
  }'
```

逐条读取 `data:` 事件，拼接 `choices[0].delta.content`；收到 `data: [DONE]` 后结束。

## 3. GPT Responses

`POST /v1/responses` 使用 `input`，以下以 `gpt-6.1-sol` 为例。

```bash
curl --silent --show-error --fail-with-body \
  "$JUHE_BASE_URL/v1/responses" \
  -H "Authorization: Bearer $JUHE_API_KEY" \
  -H 'Content-Type: application/json' \
  --data '{
    "model": "gpt-6.1-sol",
    "input": "用三句话说明单元测试的作用。",
    "max_output_tokens": 256,
    "store": false
  }'
```

在 `output` 中查找 `type: "message"`，再读取其 `content` 中 `type: "output_text"` 的 `text`。接口支持取决于所选型号，Chat Completions 与 Responses 的请求格式不能直接互换。

## 4. Claude Messages

使用 `POST /v1/messages`，以下以 `claude-opus-4-8` 为例。

```bash
curl --silent --show-error --fail-with-body \
  "$JUHE_BASE_URL/v1/messages" \
  -H "Authorization: Bearer $JUHE_API_KEY" \
  -H 'anthropic-version: 2023-06-01' \
  -H 'Content-Type: application/json' \
  --data '{
    "model": "claude-opus-4-8",
    "max_tokens": 256,
    "messages": [{"role": "user", "content": "用三句话说明数据库索引的作用。"}]
  }'
```

读取 `content` 数组中 `type: "text"` 元素的 `text`。使用系统指令时，添加顶层 `system` 字段。

流式请求设置 `stream: true`，curl 添加 `--no-buffer`。读取 `content_block_delta` 中 `delta.type: "text_delta"` 的 `delta.text`，收到 `message_stop` 后结束。

## 5. Gemini 原生格式

Gemini 原生请求使用 `POST /v1beta/models/{model}:generateContent`，以下以 `gemini-3.5-flash` 为例。

```bash
curl --silent --show-error --fail-with-body \
  "$JUHE_BASE_URL/v1beta/models/gemini-3.5-flash:generateContent" \
  -H "Authorization: Bearer $JUHE_API_KEY" \
  -H 'Content-Type: application/json' \
  --data '{
    "contents": [{"role": "user", "parts": [{"text": "用三句话说明如何安排阅读时间。"}]}],
    "generationConfig": {"maxOutputTokens": 512}
  }'
```

读取 `candidates[0].content.parts` 中的文字元素。替换型号前确认其支持所选接口；超时或输出截断的处理见 [常见报错与处理](troubleshooting.md)。
