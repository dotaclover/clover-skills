# 模型参考（实测 2026-10）

只记录跑过的事实和官方规格：能不能出图、走哪种协议、返回什么结构。**不记录价格，也不做质量排名**——好坏要自己用同一段提示词各跑几张对比。

## 一、两个系列，先选一个

| | OpenAI image 系列 | 百炼 qwen-image 系列 |
|---|---|---|
| 典型模型 | `gpt-image-2`、`gpt-image-2.5-flare`、`gpt-image-2.5-sunburst` | `qwen-image-3.0-pro`、`qwen-image-3.0`、`qwen-image-2.1-pro`、`qwen-image-2.1-turbo` |
| 默认推荐 | `gpt-image-2` | `qwen-image-3.0`（质量），`qwen-image-2.1-turbo`（性价比） |
| 需要什么 | 已有接口地址 + Key | 百炼账号，实名后自建 Key |
| 官方接入 | OpenAI Images 协议 | 三种都支持：兼容 / 同步 / 异步 |
| 图生图 | `/images/edits` multipart | 兼容模式 `generations` + `image`；DashScope `content` 数组 |

选系列的判断只有一条：**用户手上有没有 OpenAI image 系列的接口。** 有就用它；没有就推荐百炼。不要因为「qwen 便宜」擅自换系列，换系列意味着换协议、换 Key、换返回格式。

## 二、OpenAI image 系列（实测，P1）

| 模型 | 文生图 | 图生图（`/images/edits`） | 返回 |
|---|---|---|---|
| `gpt-image-2` | 200，38s，`1024x1024` / `1536x1024` 均准确 | 200，41s，`1024x1024`，确实是基于输入图 | `b64_json` + `width`/`height` + `usage` |
| `gpt-image-2.5-flare` | 200，37s，`1024x1024` | 200，53s | 同上，结构完全一致 |
| `gpt-image-2.5-sunburst` | 200，79s，`1024x1024` | 200，44s | 同上，结构完全一致 |

- 三支都是 `POST /v1/images/generations`，最小字段 `model` / `prompt` / `size` / `n` 就能出图。
- `usage.input_tokens_details.image_tokens` 在图生图时从 0 变成 200 左右，可以拿它确认输入图真的进去了。
- 单张 PNG 约 1.6–2.3MB，Base64 响应体 2.1–3.2MB，读响应别把超时设太短。
- 三支都返回 `revised_prompt`，内容通常等于原提示词。用户说「出的不是我要的」时先把它贴出来。
- 结构同构，换模型只改 `model`。

## 三、百炼 qwen-image 系列

官方模型（以控制台地域列表为准）：

| 模型 | 文生图 | 图生图 | 参考图上限 | 定位 |
|---|---|---|---|---|
| `qwen-image-3.0-pro` | ✅ | ✅ | 3 | 质量最高 |
| `qwen-image-3.0` | ✅ | ✅ | 3 | 兼顾质量与速度 |
| `qwen-image-2.1-pro` | ✅ | ✅ | 10 | I2I 参考图更多，可出透明底 |
| `qwen-image-2.1-turbo` | ✅ | ✅ | 10 | 性价比最优 |

`qwen-image-2.0` / `2.0-pro` 属上一代，字段与 2.1 一致，仍然可用；旧文档里还有 `-max` / `-plus` / `-edit-` 系列，各自只支持 T2I 或只支持编辑。名字对不上时以控制台为准。

### 实测：qwen-image-3.0 走第三方兼容层（P1）

| 场景 | 结果 | 说明 |
|---|---|---|
| 文生图 `1024x1024` | 200，67s | 尺寸准确 |
| 文生图 `1536x1024` / `1024x1536` / `1328x1328` | 200 | **尺寸全部准确生效** |
| 文生图 `n=2` | 200 | `output_image_count` 是 2，但 `data` 只有 1 项 |
| 文生图 `size=auto` | **400** | `Expected format: '<width>*<height>'` |
| 文生图 + `negative_prompt` | 200 | 该层未报错，是否生效无法从响应判断 |
| 图生图：`generations` + `image`（官方写法） | 200，但**图被丢弃** | 传猫图，出来是船 / 长椅 / 苹果，3 次都是 200 |
| 图生图：`/images/edits` multipart | 200，图有效 | 苹果→水彩苹果；**`size` 被忽略**，方图源出 `2048x2048`，竖图源出 `1664x2496` |

返回结构固定长这样（兼容层把官方 `output` 塞进了 `metadata`）：

```json
{
  "data": [{ "url": "https://...签名链接...", "b64_json": "", "revised_prompt": "" }],
  "created": 1792482166,
  "metadata": {
    "request_id": "472a7f19-...",
    "output": { "choices": [{ "message": { "content": [{ "type": "image", "image": "https://..." }] } }] },
    "usage": { "output_width": 1024, "output_height": 1024, "input_image_count": 0,
               "input_image_type": "qima_input_1k", "output_image_type": "qima_output_1k" }
  }
}
```

五个必须注意的点：

1. **`b64_json` 字段存在但是空字符串。** 判键存在就解码的代码会在这里炸。
2. **没有顶层 `width` / `height`。** 真实尺寸读 `metadata.usage.output_width/output_height`，或下载后读 PNG 头。
3. **`input_image_count` 恒为 0，别拿它判断图有没有进去。** 实测图生图成功时仍是 0。
4. **`n>1` 时 `data` 会丢图。** 两张图都在 `metadata.output.choices[].message.content[]` 里，要全就得解 `metadata`。
5. **链接是对象存储签名地址，约 24 小时过期。** 拿到就下载。

### 实测：qwen-image-2.0 / 2.0-pro

在同一个第三方地址上 `model_not_found`（HTTP 503，`No available channel for model ...`）：**该渠道只上了 3.0，没上 2.0 系**，所以没跑成。这不代表模型不存在，用它们要拿百炼自己的 Key 走 P2/P3。

## 四、怎么选

| 需求 | 建议 | 理由 |
|---|---|---|
| 用户已有 OpenAI image 接口 | `gpt-image-2` | 最小字段跑通，b64 直接落盘，不用管链接过期 |
| 只要竖版海报 | `gpt-image-2` | `1024x1536`、`1536x1024` 实测尺寸都准 |
| 想要另一种风格版本 | `gpt-image-2.5-flare` / `gpt-image-2.5-sunburst` | 同结构，只换 `model` |
| 用户没有接口，要便宜好上手 | 百炼 `qwen-image-3.0` | 实名即可开，国内不用信用卡 |
| 要一次出多张 | 百炼 2.1 / 3.0 系 | `n` 支持 1–6；但走第三方兼容层会丢图，用官方端点 |
| 要参考图多的图生图 | `qwen-image-2.1-pro` / `2.1-turbo` | 最多 10 张参考图 |
| 中文文字排版 | 自己对比 | 文字渲染必须实测，别照抄结论 |
| 图生图必须精确控尺寸 | `gpt-image-2`，或百炼官方 DashScope | 第三方兼容层的 qwen edits 不认 `size` |

## 五、模型名怎么确认

1. P1：`GET {base}/models`，取 `data[].id`，只看名字里有 `image`、`dall`、`imagen`、`flux`、`kolors` 的条目。
2. P2/P3：百炼没有统一的 models 列表可查，直接看控制台的模型广场。
3. 名字对不上**不要**自己拼一个像样的名字——拼错通常不报错，会悄悄给你默认模型的图。P1 上表现为 HTTP 503 + `model_not_found`。
4. 模型名常带版本后缀（如 `-pro`、`-turbo`、`-2026-06-22`），少一段就找不到。

## 六、这些结论的有效期

实测日期 2026-10-20，只代表那天的接口表现。模型会换版本、服务会改路由、返回字段会增加。**每次正式交付前，`prompt` 别改、`model` 换成要用的那支，跑一张确认一次**，比背结论可靠。
