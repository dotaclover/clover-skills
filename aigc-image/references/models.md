# 常用模型参考（实测 2026-10）

只记录跑过的事实：能不能出图、走哪种协议、返回什么结构。**不记录价格，也不做质量排名**——好坏要自己用同一段提示词各跑几张对比，别人的排名不可信。

## 一、默认推荐（GPT Image 系）

| 模型名 | 实测 | 尺寸 | 返回 |
|---|---|---|---|
| `gpt-image-2` | 通过 | `1024x1024`、`1024x1536` 均验证 | `b64_json` + `width`/`height` + `usage` |
| `gpt-image-2.5-flare` | 通过 | `1024x1024` | 同上，结构完全一致 |
| `gpt-image-2.5-sunburst` | 通过 | `1024x1024` | 同上，结构完全一致 |

三支都是 `POST /v1/images/generations` 的形态 A，请求体只填 `model` / `prompt` / `size` / `n` 就能出图，不需要任何私有参数。

实测细节：

- 竖图 `1024x1536` 返回的 `width` / `height` 是准确的 `1024` / `1536`，没有被改写。
- 单张 PNG 约 1.6–1.9MB，Base64 响应体 2.1–2.8MB，读响应时别把超时设太短。
- 三支都会回 `revised_prompt`，内容通常等于原提示词。用户抱怨「出的不是我要的」时，先把这个字段贴给他看。
- 结构完全同构，所以换模型只改 `model` 一个字段，其余代码不用动。

## 二、国内模型

| 模型名 | 归属 | 实测 | 关键差异 |
|---|---|---|---|
| `qwen-image-3.0` | 阿里通义千问 | 通过 | 只回 `url`，`b64_json` 是**空字符串**；无 `width`/`height` |
| `wan2.6-image` | 阿里通义万相 | 失败（400） | 不是 OpenAI 兼容形态，见下 |
| `doubao-seedream-5-0-flash-260915` | 火山方舟 | 未验证 | 模型列表里没出现，需先在方舟侧开通 |

### qwen-image-3.0

走 OpenAI 兼容路由可以正常出图，但返回结构和 GPT Image 系不一样：

```json
{
  "data": [{ "url": "https://...签名链接...", "b64_json": "", "revised_prompt": "" }],
  "created": 1792482166,
  "metadata": {
    "request_id": "472a7f19-...",
    "output": { "choices": [{ "message": { "content": [{ "type": "image", "image": "https://..." }] } }] },
    "usage": { "output_width": 1024, "output_height": 1024 }
  }
}
```

三个必须注意的点：

1. **`b64_json` 字段存在但是空字符串。** 判键存在就解码的代码会在这里炸。
2. **没有顶层 `width` / `height`。** 真实尺寸要么读 `metadata.usage.output_width/output_height`，要么下载后读 PNG 头。
3. **链接是对象存储签名地址，实测 `Expires` 比签发时间晚约 24 小时。** 拿到就下载，别攒着。

### wan2.6-image

用和上面完全相同的请求体会直接 400：

```json
{"error":{"message":"Value error, When 'enable_interleave' is False, the last message must contain 1 to 4 images. Got 0 images.: ","code":"bad_response_status_code"}}
```

这段错误来自万相自己的多模态接口，不是 OpenAI 格式的报错。说明服务端把请求转给了万相的多模态生成接口，并且：

- 该接口默认 `enable_interleave: false`，这个模式要求最后一条 message 里带 1–4 张输入图，也就是**编辑/参考图模式**；
- 纯文生图要另外传参（`enable_interleave`、`messages`、`parameters.size` 用的还是 `1024*1024` 星号写法），字段名和 OpenAI 完全不搭。

结论：`wan2.6-image` 属于形态 C（私有协议）。想用它就得按万相的多模态生成文档重写请求体，**不要把 `prompt` 塞进 OpenAI 的字段里反复试**，试多少次都是同一个 400。

### doubao-seedream-5-0-flash-260915

`GET /models` 里没有这个模型名，所以没测。用之前先在火山方舟侧确认：

1. 该模型是否已开通，账号有没有对应权限；
2. `/models` 里是否出现这个名字（没出现就别硬猜）；
3. 方舟的图片路由是 `/api/v3/images/generations`，和 OpenAI 的 `/v1/images/generations` 不是同一个路径，鉴权头也不同。

## 三、怎么选

| 需求 | 建议 | 理由（来自实测，不是主观排名） |
|---|---|---|
| 只想最快跑通一张图 | `gpt-image-2` | 最小字段即可，返回 b64 直接落盘，不用处理链接过期 |
| 需要竖版海报 | `gpt-image-2` | `1024x1536` 实测尺寸准确 |
| 想要另一种风格版本对比 | `gpt-image-2.5-flare` / `gpt-image-2.5-sunburst` | 同结构，只换 `model` |
| 指定要阿里的模型 | `qwen-image-3.0` | 能用，但要处理 url-only 返回 |
| 中文海报文字量大 | 自己对比 | 文字渲染质量必须实测，别照抄结论 |
| 指定要 Seedream | `doubao-seedream-5-0-flash-260915` | 先确认开通与路由，别按 OpenAI 路径调 |

## 四、模型名怎么确认

1. `GET {base}/models`，取 `data[].id`。
2. 只看名字里有 `image`、`dall`、`flux`、`imagen`、`seedream`、`qwen-image`、`wan`、`kolors`、`sd` 的条目。
3. 名字对不上就**不要**自己拼一个像样的名字——拼错通常不会报错，会悄悄给你默认模型的图。
4. 同一个服务里，模型名可能带版本后缀（如 `-260915`、`-flash`），少一段就找不到。

## 五、这些结论的有效期

实测日期 2026-10-20，只代表那天的接口表现。模型会换版本、服务会改路由、返回字段会增加。**每次正式交付前，`.prompt` 别改、`.model` 换成要用的那支，跑一张确认一次**，比背结论可靠。
