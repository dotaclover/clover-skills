---
name: baidu-vod
description: 直连百度 VOD 的 OpenAI 兼容聊天接口，适用于旧 VOD 或新 VOD 的鉴权、模型验证和 Chat Completions 调用；不用于百度千帆、百度 AI 网关或视频任务。
---

# 百度 VOD 直连

使用独立的 VOD Base URL 和 Bearer API Key。旧 VOD 与新 VOD 的地址、密钥和模型权限互不通用；调用前先确认使用的是哪一种。

## 工作流

1. 按 [接口与 cURL](references/api.md) 设置对应环境变量，并把 Base URL 保持在服务根地址。
2. 从 [模型与验证](references/models.md) 选择候选模型；历史可用记录只作起点，当前账号仍须实际验证。
3. 只读检查可直接运行脚本的 `--help`。发送聊天请求前必须明确使用 `--send`，因为模型调用可能产生费用。

```powershell
# 旧 VOD：实际发送请求前必须加 --send
python scripts/chat_smoke.py --provider old --model glm-5.3 --send

# 新 VOD：使用新 VOD 自己的地址和 Key
python scripts/chat_smoke.py --provider new --model glm-5.3 --send
```

## 必须保持的边界

- 旧 VOD 的示例 Base URL 是 `https://vod.bj.baidubce.com/v3/chat/oc`；新 VOD 的示例 Base URL 是 `https://vod.gz.baidubce.com`。两者都在其 Base URL 后追加 `/v1/chat/completions`。
- 仅使用 `Authorization: Bearer <API_KEY>`。不要将 Qianfan token、百度 AI 网关 Key 或其他供应商凭据用于 VOD。
- 当前不以 `/v1/models` 的结果作为 VOD 的可靠模型发现依据；从候选模型开始逐个实际调用验证。
- 本技能仅覆盖 OpenAI Chat Completions 兼容聊天。百度 VOD 的视频创建、任务查询和异步结果协议未在此技能中确认，不能据此宣称支持视频生成。
- 不把真实 API Key、完整请求头、签名 URL 或完整上游响应写入 Git、公共终端日志或技能文件。

\n