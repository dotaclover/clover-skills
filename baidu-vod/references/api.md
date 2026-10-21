# 接口与 cURL

## 配置

```bash
export BAIDU_VOD_URL='https://vod.bj.baidubce.com/v3/chat/oc'
export BAIDU_VOD_KEY='<旧 VOD API Key>'

export BAIDU_NEWVOD_URL='https://vod.gz.baidubce.com'
export BAIDU_NEWVOD_KEY='<新 VOD API Key>'
```

## 旧 VOD 聊天

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

## 新 VOD 聊天

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