# 三种接口形态与通用范式

同样是「给个 prompt 出图」，三家供应商可能给出三种完全不同的调用方式。先定性，再写代码；定性错了，后面全是白试。

## 怎么快速定性

| 观察 | 结论 |
|---|---|
| 文档写 `POST /v1/images/generations`，示例响应里有 `data[0].b64_json` 或 `data[0].url` | 形态 A：同步 |
| 提交后只返回 `id`、`task_id`、`request_id`、`prediction id`，还要再查一次 | 形态 B：异步任务 |
| 文档只有 `POST /v1/chat/completions`，或路由长得不像图片接口 | 形态 C：私有协议 |

不确定就直接调一次最小的真实请求，**看响应体长什么样再决定**。不要凭供应商名字猜。

---

## 形态 A · 同步返回

一次请求拿到图，最省事。

```
POST {base}/images/generations
→ 200 后立即从 data[0] 取 b64_json 或 url
```

关键点：

- 连接必须长时间开着，超时要放宽到 480 秒以上。
- 返回 `text/html` 说明打到了前端页面（路径缺 `/v1`、或该服务没有这个路由），不是接口报错。
- 不支持流式的话不要带 `stream`。

适用：OpenAI 官方及绝大多数标称「OpenAI 兼容」的生图服务。

---

## 形态 B · 异步任务

提交只拿任务号，结果要轮询或等回调。国内大厂（火山、阿里、百度、腾讯）和 fal / Replicate 这类平台基本都是这套。

### 通用三段式

```
1) 提交   POST {base}/...            → { "task_id": "abc" }
2) 轮询   GET  {base}/.../{task_id}  → { "status": "running|succeeded|failed", "output": ... }
3) 下载   从 output 里取 url，落盘转存
```

### 轮询纪律

| 项 | 建议 |
|---|---|
| 间隔 | 3–5 秒，不要 200ms 高频打 |
| 上限 | 60–120 次（约 5–10 分钟），超时判「仍在生成」，把 task_id 留给用户 |
| 状态词 | 各家不同：`queued`/`pending`/`running`/`processing`/`succeeded`/`failed`/`cancelled`。别只认一种 |
| 失败 | 读 `error` / `fail_reason` 原文，不要自己总结成「生成失败」 |
| 重试 | 任务已经提交成功就**不要重新提交**，重提会重复计费 |

### 各家形态对照（只记结构，不记死地址）

| 供应商风格 | 提交 | 查询 | 结果位置 |
|---|---|---|---|
| fal 系 | 平台文档给出的队列提交端点 | 响应里自带 `status_url` / `response_url` | `response_url` 返回的 JSON 内图片 URL 数组 |
| Replicate 系 | `POST /v1/predictions` | 响应自带 `urls.get` | `output` 字段，可能是字符串或数组 |
| 国内云厂商 | `POST /api/v3/images/generations` 或带 `Action=` 的 query 路由 | `GET .../tasks/{id}` | `data[].url` 或 `result.images[]` |

**地址以用户提供的文档为准**。上表只用于判断「响应里该找哪个字段」，不要据此拼 URL。

### 结果 URL 会过期

异步任务的产物链接几乎都是签名 URL，常见 1 小时到 24 小时失效。拿到就立刻下载到本地，并保存原始链接备查。

---

## 形态 C · 私有协议 / chat 路由

有些服务把图片塞进聊天接口：

```json
{
  "model": "<模型名>",
  "messages": [{"role": "user", "content": "<提示词>"}],
  "modalities": ["image", "text"]
}
```

图片可能出现在：

- `choices[0].message.content` 里的 Markdown 链接 `![](https://...)`
- 独立的 `choices[0].message.images[]` 数组
- base64 字段（字段名各家自定，如 `b64_json`、`image_base64`、`data`）

**实测判据（2026-10）**：`wan2.6-image` 用标准 OpenAI 请求体打 `/v1/images/generations`，返回的是

```json
{"error":{"message":"Value error, When 'enable_interleave' is False, the last message must contain 1 to 4 images. Got 0 images.: ","code":"bad_response_status_code"}}
```

`enable_interleave`、`messages` 这些词不是 OpenAI 的，出现即说明服务端把请求转给了另一套协议（这里是万相的多模态生成接口）。**看到「字段像 OpenAI、报错术语却是别家」的 400，直接判定形态 C**，不要再换参数试。

处理原则：

1. 先把一次真实响应的结构打印出来（去掉超长 base64），确认图片在哪。
2. 用正则或字段遍历兜底：找 `http(s)://...\.(png|jpg|jpeg|webp)`，再找长度超过 5000 的 base64 字符串。
3. 兜底成功也要在报告里写清「按字段猜测取的图」，不要假装是规范返回。

---

## 三种形态的共性纪律

1. **地址、Key、模型全部来自用户**，技能里没有默认值。
2. **先最小请求**（模型 + 提示词 + 尺寸 + 1 张），跑通再加参数。
3. **长超时 + 后台**：出图 20 秒到 2 分钟都正常，别用默认 120 秒卡死。
4. **中断先查落盘**：请求被杀不等于没出图，服务端可能已经计费。
5. **一次成功就停**：追加生成要用户点头。
6. **原始响应留档**：脱敏后的请求、curl、响应三件套，出问题才有得查。
