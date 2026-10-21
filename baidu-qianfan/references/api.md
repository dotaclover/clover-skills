# 接口与 cURL

## 配置

```bash
export BAIDU_QF_URL='https://qianfan.baidubce.com'
export BAIDU_QF_KEY='<千帆 API Key>'
```

## 模型目录

```bash
curl --fail-with-body -sS "$BAIDU_QF_URL/v1/models" \
  -H "Authorization: Bearer $BAIDU_QF_KEY"
```

## Chat Completions

```bash
curl --fail-with-body -sS "$BAIDU_QF_URL/v2/chat/completions" \
  -H "Authorization: Bearer $BAIDU_QF_KEY" \
  -H 'Content-Type: application/json' \
  --data '{
    "model": "glm-5.3",
    "messages": [{"role": "user", "content": "你好，请用一句话回答。"}],
    "max_tokens": 128,
    "stream": false
  }'
```

## 其他接口

| 能力 | 方法 | 路径 |
| --- | --- | --- |
| 向量 | POST | `/v2/embeddings` |
| 图像生成 | POST | `/v2/images/generations` |
| 图像编辑 | POST | `/v2/images/edits` |
| 重排序 | POST | `/v2/rerank` |