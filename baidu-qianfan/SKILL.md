---
name: baidu-qianfan
description: 直连百度智能云千帆 Qianfan，提供模型目录、OpenAI 兼容推理和 Seedance FireSeries 视频任务的接口与示例。
---

# 百度千帆 Qianfan 直连

## 能力

- 模型目录：`GET /v1/models`
- 聊天：`POST /v2/chat/completions`
- 向量：`POST /v2/embeddings`
- 图像生成：`POST /v2/images/generations`
- 图像编辑：`POST /v2/images/edits`
- 重排序：`POST /v2/rerank`
- Seedance 视频：FireSeries 创建和任务查询

## 对接

```bash
export BAIDU_QF_URL='https://qianfan.baidubce.com'
export BAIDU_QF_KEY='<千帆 API Key>'
```

所有接口使用 `Authorization: Bearer $BAIDU_QF_KEY`。

- 接口与 cURL 示例：[references/api.md](references/api.md)
- 可用模型：[references/models.md](references/models.md)
- Seedance 视频：[references/seedance.md](references/seedance.md)

```powershell
python scripts/qianfan.py models
python scripts/qianfan.py chat --model glm-5.3 --send
```