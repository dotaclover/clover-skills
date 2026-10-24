---
name: baidu-vod
description: 直连百度 VOD 的 OpenAI Chat Completions 服务，提供旧 VOD、新 VOD 的地址、鉴权、模型和调用示例。
---

# 百度 VOD 直连

## 能力

- 旧 VOD：OpenAI Chat Completions。
- 新 VOD：OpenAI Chat Completions。

## 对接

| 服务 | Base URL | 环境变量 | 请求地址 |
| --- | --- | --- | --- |
| 旧 VOD | `https://vod.bj.baidubce.com/v3/chat/oc` | `BAIDU_VOD_URL`、`BAIDU_VOD_KEY` | `/v1/chat/completions` |
| 新 VOD | `https://vod.gz.baidubce.com` | `BAIDU_NEWVOD_URL`、`BAIDU_NEWVOD_KEY` | `/v1/chat/completions` |

鉴权：`Authorization: Bearer <API Key>`。

历史入口原文保留；当前接口与模型请改读合并技能的 `references/vod-api.md` 和 `references/vod-models.md`。

```powershell
python scripts/chat_smoke.py --provider old --model glm-5.3 --send
python scripts/chat_smoke.py --provider new --model glm-5.3 --send
```