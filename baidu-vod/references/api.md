# 接口与 cURL

## 环境变量

```bash
# 旧 VOD
export BAIDU_VOD_URL='https://vod.bj.baidubce.com/v3/chat/oc'
export BAIDU_VOD_KEY='<旧 VOD API Key>'

# 新 VOD
export BAIDU_NEWVOD_URL='https://vod.gz.baidubce.com'
export BAIDU_NEWVOD_KEY='<新 VOD API Key>'
```

PowerShell 使用 `$env:BAIDU_VOD_URL` 和 `$env:BAIDU_VOD_KEY`，或对应的 `BAIDU_NEWVOD_*` 变量。不要把 Key 写入命令历史、截图或源代码。

## Chat Completions

两个版本都使用 OpenAI Chat Completions 风格请求，端点为：

```text
POST {BAIDU_VOD_URL}/v1/chat/completions
POST {BAIDU_NEWVOD_URL}/v1/chat/completions
Authorization: Bearer <对应 API Key>
Content-Type: application/json
```

旧 VOD 示例：

```bash
curl --fail-with-body -sS "$BAIDU_VOD_URL/v1/chat/completions" \
  -H "Authorization: Bearer $BAIDU_VOD_KEY" \
  -H 'Content-Type: application/json' \
  --data '{
    "model": "glm-5.3",
    "messages": [{"role": "user", "content": "你好，请用一句话介绍自己。"}],
    "max_tokens": 128,
    "stream": false
  }'
```

新 VOD 仅替换地址和 Key：

```bash
curl --fail-with-body -sS "$BAIDU_NEWVOD_URL/v1/chat/completions" \
  -H "Authorization: Bearer $BAIDU_NEWVOD_KEY" \
  -H 'Content-Type: application/json' \
  --data '{
    "model": "glm-5.3",
    "messages": [{"role": "user", "content": "你好"}],
    "max_tokens": 64,
    "stream": false
  }'
```

## 常见问题

- 返回签名格式错误：确认请求发往追加后的 `/v1/chat/completions`，而不是直接请求 Base URL。
- 401 或 403：核对 VOD 版本、Key 和账号模型权限；不要改用千帆或 AI 网关的 Key 重试。
- 404：先检查旧 VOD 是否误用了新 VOD 地址，或新 VOD 是否误加了旧地址中的 `/v3/chat/oc`。
- 模型错误：模型目录和历史记录都不能替代当前 Key 的实际调用结果。

\n