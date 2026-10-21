# 接口与 cURL

## 配置

```bash
export BAIDU_QF_URL='https://qianfan.baidubce.com'
export BAIDU_QF_KEY='<千帆 API Key>'
```

所有示例使用：

```text
Authorization: Bearer <BAIDU_QF_KEY>
Content-Type: application/json
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

## 其他兼容接口

根据模型和账号开通情况，千帆还提供以下路径。请求字段以调用时的千帆官方模型文档为准：

| 能力 | 方法 | 路径 |
| --- | --- | --- |
| 向量 | POST | `/v2/embeddings` |
| 图像生成 | POST | `/v2/images/generations` |
| 图像编辑 | POST | `/v2/images/edits` |
| 重排序 | POST | `/v2/rerank` |

不要因为端点存在就假定任何模型或 Key 有权限。对生产工作流应先使用非敏感输入做一次最小验证。

## 故障处理

- 401/403：检查千帆 Key、账号开通状态和模型权限，勿使用 VOD 或 AI 网关的 Key。
- 404：确认 Base URL 没有携带其他产品的路径，并检查端点版本是否为 `/v2/...`。
- 模型错误：目录可见不代表可调用；记录 HTTP 状态和脱敏错误后改用当前账号已开通的模型。
- 流式响应：保留 `stream: true`，按 SSE 协议逐条消费；不要把多条事件拼成一个 JSON 对象解析。

\n