---
name: aigc-image
display_name: 图片生成接口
display_name_en: Image Generation API
description: "用用户自备的接口地址与 Key 调用图片生成 API：先判定同步 / 异步任务 / 私有协议三种接口形态，再选模型、构造参数、提交生成、解析 url 或 b64_json、保存并校验图片，给出可复现的 curl 与 SDK 示例。适用于调用 OpenAI 兼容格式的生图接口、做接口兼容性验证、按错误码排错；附 GPT Image 系、Qwen-Image、万相、Seedream 的实测差异参考。不预置接口地址与 Key，模型名以 /models 返回为准；不用于视频生成，也不替代平台内置的图片生成能力。"
description_zh: "把接口地址与 Key 交给用户自己填：判定接口形态、挑选模型、核对参数、提交生成、解析 base64 或图片链接，出图后校验尺寸与文字，报错时按状态码定位原因。"
description_en: 'Call any image generation API with an endpoint and key you provide: detect the API shape, pick a model, verify parameters, submit, decode base64 or download the returned URL, then check the image size and rendered text. Includes measured notes on GPT Image, Qwen-Image, Wan and Seedream. No endpoint or key is bundled.'
examples_zh:
  - '用我自己的接口生成一张竖版海报'
  - '帮我验证这个图片接口能不能出图'
  - '查一下这个接口报401的原因'
examples_en:
  - 'Generate a vertical poster through my own image API'
  - 'Check whether this image endpoint and key work'
  - 'My image API returns 401 — find the cause'
version: 1.0.1
author: 独立开发者
agent_created: true
---

# 通用图片生成接口

这个技能只提供**接口说明、参数含义、可复现示例和排错方法**。接口地址、Key、模型名一律由用户提供——技能里没有默认值，也不该有。

现在绝大多数生图服务都以 OpenAI 兼容格式对外提供接口：除了 OpenAI 自己，国内不少大厂也这么做（阿里、火山、百度、腾讯等），还有大量独立服务商和自建服务。字段覆盖程度各家不同，同一个模型名在不同服务上支持的范围也可能不一样。所以一切以手上那份接口文档和 `GET {base}/models` 的返回为准。

## 该用 / 不该用

| 场景 | 判断 |
|---|---|
| 用户给了接口地址 + Key，要走 OpenAI 兼容格式的生图接口出图 | ✅ 主场景 |
| 验证某个生图网站是否真兼容 OpenAI 图片格式 | ✅ 走兼容性检查 |
| 用户问 `size`、`quality`、`response_format` 到底怎么填 | ✅ 查 `references/openai-compatible.md` |
| 用户问 GPT Image、Qwen-Image、万相、Seedream 该选哪个 | ✅ 查 `references/models.md` |
| 出图报 400 / 401 / 429，要定位原因 | ✅ 查 `references/troubleshooting.md` |
| 用户只说「画张图」，没提接口 | ❌ 用平台内置图片生成能力，不要自己编一个接口 |
| 用户要生成视频 | ❌ 走视频类技能 |
| 用户问某家模型多少钱、怎么充值 | ❌ 不猜价格，让他看服务商自己的价目页 |

## 一、常用模型参考

以下按实测结果标注，只写验证过的事实，不写没跑过的好坏结论。

| 模型名 | 来源 | 实测（2026-10） | 关键差异 |
|---|---|---|---|
| `gpt-image-2` | GPT Image 系，**默认首选** | 200，`1024x1024` 与竖图 `1024x1536` 均正常 | 返回 `b64_json` + `width`/`height` + `usage` |
| `gpt-image-2.5-flare` | GPT Image 系，**默认首选** | 200，`1024x1024` | 与 `gpt-image-2` 同构返回 |
| `gpt-image-2.5-sunburst` | GPT Image 系，**默认首选** | 200，`1024x1024` | 与 `gpt-image-2` 同构返回 |
| `qwen-image-3.0` | 阿里通义千问 | 200，`1024x1024` | **只给 `url`**，`b64_json` 是空字符串；签名链接约 24 小时过期 |
| `wan2.6-image` | 阿里通义万相 | 400 | 不是 OpenAI 兼容形态，走 `/images/generations` 会报 `enable_interleave` / `messages` 相关错误，必须换成万相自己的多模态生成接口 |
| `doubao-seedream-5-0-flash-260915` | 火山方舟 | 未验证 | 需要先在方舟侧开通，模型列表里出现之前调不通 |

默认先试 GPT Image 系这三支。**模型名写错不一定报错**，不少服务会悄悄回落成默认模型，所以出图风格不对劲时先回头核对实际模型名。

各家的参数支持范围、返回结构差异、选型建议见 `references/models.md`。

## 二、开工前必须拿到的四项

| 项 | 说明 | 缺了会怎样 |
|---|---|---|
| 接口根地址 | 形如 `https://<host>/v1`，含版本段 | 拼错路径会拿到前端 HTML，不是 JSON |
| 鉴权方式 | 多数是 `Authorization: Bearer <key>`，少数是 `x-api-key` 或 query 参数 | 401 且看不出原因 |
| API Key | 用户当场提供或已存在环境变量里 | 不能调用 |
| 模型名 | 从 `GET {base}/models` 取，或用户指定 | 404 / 模型被静默替换 |

**四条硬规则：**

1. 地址、Key、模型都不猜。缺哪项就直接问，不要拿上一次会话的 Key 顶上。
2. 真实 Key 只走环境变量或请求头，不写进技能文件、请求 JSON、报告和最终回复。示例里统一写 `$IMAGE_API_KEY`、`<BASE_URL>`。
3. 默认 `n: 1`。用户没说数量就不批量，避免无意产生费用。
4. 一次成功就停。追加生成、换模型重试都要用户明确说要。

## 三、先判定接口形态（决定后面全部写法）

| 形态 | 特征 | 后续步骤 |
|---|---|---|
| **A. OpenAI 兼容同步** | `POST {base}/images/generations`，响应里直接有 `data[0].b64_json` 或 `data[0].url` | 最短路径，见 `references/openai-compatible.md` |
| **B. 异步任务** | 提交只返回 `id` / `task_id` / `request_id`，要再查状态 | 提交 → 轮询 → 下载 → 转存，见 `references/api-patterns.md` |
| **C. 私有协议** | 只有 `/chat/completions` 或自定义路由；图片藏在 Markdown 链接、消息内容或 base64 字段里 | 按服务商文档拼，参数别照搬 OpenAI |

判定办法：先 `GET {base}/models` 看返回结构；拿不准就让用户贴一段文档或一次真实响应。**不要**拿 OpenAI 的参数去套私有协议，字段名不同会静默失败（HTTP 200 但没图），或者像 `wan2.6-image` 那样直接 400。

同一个服务里，有的模型是形态 A，有的模型是形态 C，别按服务商一刀切，要按模型逐个确认。

## 四、五步流程

### 步骤 0 · 验鉴权 + 列模型

```bash
curl -sS "$IMAGE_BASE_URL/models" \
  -H "Authorization: Bearer $IMAGE_API_KEY"
```

返回 `200` + `{"data":[{"id":"..."}]}` 说明地址、鉴权都对。从 `data[].id` 里挑图片类模型名（含 `image`、`dall`、`flux`、`imagen`、`seedream`、`qwen-image`、`wan` 等）。**只见过名字不等于验证过它能出图**，不要说「已支持」。

### 步骤 1 · 写提示词

提示词至少覆盖：主体、用途、构图、风格、画幅、必须出现的文字、禁止元素（水印、第三方 Logo）。海报类要把文案逐条写进 prompt，生成后必须目视核对拼写。

### 步骤 2 · 构造请求

只填最小兼容字段 `model` / `prompt` / `size` / `n`，先跑通一次。服务商私有参数（`seed`、`negative_prompt`、`steps`、`guidance_scale`、`watermark`、`enable_interleave`）等跑通后再加——一上来堆参数，出错分不清是谁的问题。

完整参数见 `references/openai-compatible.md`，可直接改的 curl / Python / Node / SDK 示例见 `references/examples.md`。

### 步骤 3 · 提交（长超时 + 后台）

出图不是秒回。单张常见 20–60 秒，高质量或大尺寸超过 2 分钟很正常。**默认 120 秒的前台超时会杀掉 curl，但服务端往往已经跑完并计费。**

- 生成请求一律加 `--max-time 480`，并放后台跑。
- 被中断先看响应文件是否已写入，确认没出图再重试，别盲目重发。
- 异步形态记得**轮询上限**（例如 60 次 × 5 秒），超了就报「仍在生成」，不要无限等。

### 步骤 4 · 解析并保存

两种返回必须都兼容，**判空不要判字段是否存在**：`qwen-image-3.0` 会返回 `"b64_json": ""`，字段在但是空的。

| 字段 | 处理 |
|---|---|
| `data[0].b64_json` 非空 | Base64 解码后写成图片文件。**绝不把整段 Base64 贴给用户** |
| `data[0].url` 有值 | 存下原始 URL，立刻下载转存。签名链接会过期（实测约 24 小时） |
| 两者都空 | 说明接口形态判断错了，回第三章 |

文件名带模型、尺寸、序号，例如 `image-<model>-1024x1536-01.png`。同时保留请求 JSON、脱敏后的 curl、原始响应，方便复现。

### 步骤 5 · 校验

- 文件能解码、能打开，不是 0 字节、不是 HTML 错误页。
- PNG 宽高（偏移 16 与 20 处的大端 uint32）与请求尺寸一致；不一致说明服务端改了尺寸，要写进报告。
- 主体、构图、品牌色、用途符合提示词。
- 文字没拼错、没乱码、没缺字。
- 没有用户禁止的水印或 Logo。
- 需要透明底时确认真的带 alpha 通道（多数接口要求同时指定 `background: transparent` **和** `output_format: png|webp`）。

## 五、核心参数速查

| 参数 | 必填 | 常见取值 | 坑 |
|---|---|---|---|
| `model` | ✅ | 从 `/models` 取 | 名字错不一定报错，服务可能悄悄换成默认模型 |
| `prompt` | ✅ | 中英文均可 | 文字渲染差是模型问题，不是参数问题 |
| `n` | 否 | `1`（默认值就用 1） | 部分模型只支持 1；`n>1` 按张计费 |
| `size` | 否 | `1024x1024` / `1536x1024` / `1024x1536` / `auto` | 各模型支持集合不同，乱填常被静默改成正方形；万相系用 `1024*1024` 这种星号写法 |
| `quality` | 否 | `low` / `medium` / `high` / `auto`；老模型是 `standard` / `hd` | 两套枚举不通用 |
| `response_format` | 否 | `url` / `b64_json` | 新模型往往只给 `b64_json`，强制 `url` 可能 400 或被忽略 |
| `background` | 否 | `transparent` / `opaque` / `auto` | 透明底必须配 png/webp |
| `output_format` | 否 | `png` / `jpeg` / `webp` | 与 `background: transparent` 冲突时透明失效 |
| `user` | 否 | 任意稳定标识 | 只用于服务商侧风控溯源，不影响出图 |

图生图 / 局部重绘走 `POST {base}/images/edits`，`multipart/form-data`，字段是 `image`（可多张）、`mask`、`prompt`。**用户提供的参考图必须他自己有使用权**，不接受来源不明的图。

## 六、失败处理

先看 HTTP 状态和响应体的 `error.message`，按 `references/troubleshooting.md` 对照。高频四类：

| 状态 | 常见含义 | 正确动作 |
|---|---|---|
| 401 / 403 | Key 错、Key 无该模型权限、Key 分组不对 | 让用户核对 Key 与模型授权，不要换地址试 |
| 404 | 路径少了 `/v1`、或该服务没有这个路由 | 核对 base URL，别猜新路径 |
| 400 | 尺寸/质量枚举不支持、提示词被内容策略拦截、模型根本不是这个协议的 | 读 `error.message`，先判断是不是模型选错 |
| 429 | 限流或额度耗尽 | 看 `Retry-After`；额度问题直接告知用户，别循环重试 |

**不要**连续换模型重试付费请求。每次失败都要能说清「改了什么、为什么这么改」。

## 七、已知坑（实测，2026-10）

- **默认 120 秒前台超时会杀掉 curl，服务端往往已经出图并计费。** 生成请求一律 `--max-time 480` 放后台执行。
- **不支持的 `size` 常被静默改成 `1024x1024`，不报错。** 出图后必须读回真实宽高。
- **`b64_json` 字段存在但是空字符串。** `qwen-image-3.0` 就是这样，必须判空值而不是判键是否存在。
- **新模型默认只返回 `b64_json`，`response_format: "url"` 会被忽略。** 两个字段都要判空，别只写一个分支。
- **路径少写 `/v1` 时，返回的可能是前端 HTML，HTTP 状态还是 200。** 先看响应体开头是 `{` 还是 `<`。
- **部分服务把不认识的 `model` 悄悄回落成默认模型。** 出图风格与预期不符时才暴露，报告里要写实际用的名字。
- **`base64.b64decode` 遇到 `data:image/png;base64,` 前缀会直接报错。** 先 `split(",", 1)[-1]`。
- **429 有两种。** 限流可退避后重试一次；额度耗尽或欠费重试只会继续失败，直接告知用户。
- **异步任务拿到 `task_id` 就不要重提。** 重提等于重新排队、重新计费，先查状态。
- **同一个服务里模型协议可能不统一。** `qwen-image-3.0` 走 OpenAI 兼容路由正常，同门的 `wan2.6-image` 走同一路由直接 400。

## 八、报告格式

- 鉴权是否通过，不显示 Key。
- `/models` 是否可用、命中哪些图片模型。
- 实际使用的接口形态、base URL（脱敏后的 host 即可）、模型、尺寸、`n`。
- HTTP 状态、返回类型（`b64_json` / `url`）、文件大小、本地图片路径。
- 请求 JSON、脱敏 curl、原始响应的保存位置。
- 尺寸是否被服务端改写、文字是否需人工复核、透明底是否生效。
- 若失败：原始错误码和 `error.message` 原文，不做美化。

## 九、参考资料

| 文件 | 什么时候读 |
|---|---|
| `references/models.md` | 要在 GPT Image 系、Qwen-Image、万相、Seedream 之间选模型，或想确认某个模型名到底走哪种协议 |
| `references/openai-compatible.md` | 要确认某个参数的合法取值、模型差异、`/images/generations` 与 `/images/edits` 的完整字段 |
| `references/api-patterns.md` | 接口是异步任务型、或只有 chat 路由、或响应结构不是标准 OpenAI 时 |
| `references/examples.md` | 要直接抄一份 curl / Python requests / Node fetch / OpenAI SDK 的调用代码，含解码与保存 |
| `references/troubleshooting.md` | 报错、超时、出了图但打不开、尺寸不对、URL 过期、返回 HTML 而不是 JSON |
