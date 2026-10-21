---
name: baidu-qianfan
description: 直连百度智能云千帆 Qianfan 的模型目录、OpenAI 兼容推理和 Seedance FireSeries 视频任务；不用于百度 VOD 或百度 AI 网关。
---

# 百度千帆 Qianfan 直连

直接使用千帆 Base URL `https://qianfan.baidubce.com` 和该账号的 Bearer API Key。它与百度 VOD、百度 AI 网关的地址、密钥和 Seedance 协议互不通用。

## 工作流

1. 先读 [接口与 cURL](references/api.md)，设置 `BAIDU_QF_URL` 与 `BAIDU_QF_KEY`。
2. 调用模型目录后，仍按 [模型与验证](references/models.md) 用最小聊天请求验证实际权限。
3. 需要 Seedance 视频时读 [FireSeries 视频任务](references/seedance.md)，先获得明确的付费授权再创建任务，并查询至终态。

```powershell
# 只读列出模型
python scripts/qianfan.py models

# 会实际调用模型，必须明确加 --send
python scripts/qianfan.py chat --model glm-5.3 --send
```

## 必须保持的边界

- 文本和向量接口的 Base URL 是 `https://qianfan.baidubce.com`，使用 Bearer API Key。不能替换为百度 VOD 地址或百度 AI 网关地址。
- `/v1/models` 只反映目录，不证明当前 Key 可调用某个模型；首次使用任何模型都要做最小真实请求。
- Seedance FireSeries 只使用 Qianfan 的 `/beta/video/generations/qianfan-video/fireseries`；模型短名是 `S2.0`、`S2.0-Fast`、`S2.0-Mini` 和 `S2.5`。
- FireSeries 创建成功只代表任务已受理。必须使用任务查询接口确认最终状态和结果，不能把排队或运行中当作成片。
- 未确认 Qianfan FireSeries 的原生素材资产管理协议。不要把百度 AI 网关的 `Action=CreateAsset`、`asset://` 或真人 H5 协议当作 Qianfan 的接口。
- API Key、任务结果中的临时媒体 URL 和完整原始响应只保存在私有环境，不能提交到 Git 或公开日志。

\n