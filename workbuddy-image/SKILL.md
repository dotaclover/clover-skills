---
name: workbuddy-image
display_name: 图片生成接口
display_name_en: Image Generation API
description: "用自己的接口地址和 Key 出图，支持文生图与图生图。自带脚本，没 Key 也能验参数、拼请求；有 Key 一条命令出图并核对尺寸。支持 OpenAI 兼容接口与阿里云百炼 qwen-image，附公众号、小红书等常用尺寸模板。"
description_zh: "用自己的接口出图，文生图和图生图都支持。自带脚本，没 Key 也能验参数、拼请求；有 Key 一条命令出图。附公众号、小红书常用尺寸模板。"
description_en: 'Text-to-image and image editing with your own API endpoint and key. Ships with an offline-capable CLI: validate parameters and build requests without a key, then generate and verify sizes once configured. Supports OpenAI-compatible endpoints and Alibaba Cloud Bailian qwen-image, with size presets for WeChat and Xiaohongshu covers.'
examples_zh:
  - '用我的接口生成一张竖版海报'
  - '帮我验证这个图片接口能不能出图'
  - '把这张图改成水彩画风格'
examples_en:
  - 'Generate a vertical poster through my own image API'
  - 'Check whether this image endpoint and key work'
  - 'Turn this photo into a watercolor painting'
version: 1.0.1
author: 独立开发者
agent_created: true
---

# 图片生成接口

用自己的接口地址和 Key 出图。**不预置接口地址、模型默认值或 Key**；唯一写死的域名是阿里云百炼官方 API，因为那是推荐路径。

自带 `scripts/image_api.py`，纯标准库，Python 3.8+，**不需要 pip 装任何东西**。下面命令里的 `python3` 在 Windows 上换成 `python` 即可。

## 快速开始

```bash
# 1. 先自检，确认脚本可用（不需要网络和 Key）
python3 scripts/image_api.py self-test

# 2. 存一次接口地址和 Key，之后不用每次传
python3 scripts/image_api.py init
# 也可以一条命令带参数：init --base-url https://your-host/v1 --key sk-xxx

# 3. 校验参数并生成请求体（不发请求、不花钱）
python3 scripts/image_api.py build --proto openai --model gpt-image-2 \
  --prompt "一只橘猫坐在窗台上" --size 1024x1536 --n 1 --out req.json

# 4. 出图并取回本地
python3 scripts/image_api.py send --proto openai --request req.json --out resp.json
python3 scripts/image_api.py save --response resp.json --out-dir out --expect-size 1024x1536
```

`init` 问答式引导，把地址和 Key 存到 `~/.aigc-image/config.json`，下次 `send` / `probe` 不用再传。`init --show` 查看当前配置（Key 只显示头尾）。这个文件是明文，别提交到 Git。

`save` 会打印真实宽高。跟请求不一致会标 `size_mismatch`——服务端没照你说的尺寸出图，必须写进报告。

## 常用模板（内容由用户补）

模板只给尺寸、比例和风格骨架，**具体画什么由用户说**，提示词里留 `【用户补充的内容】` 占位。

| 场景 | id | 尺寸 | 比例 | 适合 |
|---|---|---|---|---|
| 公众号封面首图 | `wechat-cover` | 1536x1024 | 3:2 | 左侧留白放标题 |
| 公众号正文配图 | `wechat-inline` | 1024x1024 | 1:1 | 扁平插画，多图并排不亏 |
| 小红书封面 | `xhs-cover` | 1024x1536 | 2:3 | 上方留标题区 |
| 小红书实拍感 | `xhs-photo` | 1024x1024 | 1:1 | 要「不像 AI 生成」用这个 |
| 竖版海报 | `poster` | 1024x1536 | 2:3 | 留标题与卖点位 |
| 头像 / 人物图 | `avatar` | 1024x1024 | 1:1 | 半身正面，留裁切余量 |

```bash
python3 scripts/image_api.py presets                 # 看全部
python3 scripts/image_api.py presets --id xhs-cover  # 看完整提示词
python3 scripts/image_api.py presets --scene 公众号   # 按场景过滤
```

**提问时就照这个问，一次只问场景和内容两件事：**

> 这张图用在哪？
> - 公众号封面（1536x1024，左边留白放标题）
> - 小红书封面（1024x1536 竖图，上面留标题区）
> - 方图 / 头像（1024x1024）
>
> 内容你写一句就行，风格和参数我来补。

三条提前说清，别等交付后再扯：

- 公众号官方封面是 **2.35:1**，两家接口都不直接支持。按 1536x1024 出图，再裁成 900x383。
- 小红书主流 **3:4**，接口只给 2:3，出图后上下各裁一点就接近。
- **文字别让模型直接写**，小字容易糊，出图后自己加。

## 命令速查

| 子命令 | 要 Key | 干什么 |
|---|---|---|
| `presets` | 否 | 看常用尺寸模板：公众号、小红书、海报、头像 |
| `self-test` | 否 | 24 项离线自检 |
| `init` | 否 | 保存地址与 Key，`init --show` 查看（Key 打码） |
| `validate` | 否 | 查模型名、size 写法、像素范围、宽高比、n 上限 |
| `build` | 否 | 输出请求体 JSON + 等价 curl |
| `size` | 否 | 读 PNG/JPEG 头报真实宽高 |
| `probe` | 是 | `GET {base}/models`，列模型并标出图片类 |
| `send` | 是 | 发请求，超时 480 秒，不走系统代理，存原始响应 |
| `save` | 否 | 解析 url 或 base64，落盘并核对尺寸 |

`--proto` 四个取值：`openai`（文生图 / qwen 图生图，JSON）、`openai-edit`（multipart 图生图）、`dashscope`（百炼同步）、`dashscope-async`（百炼异步）。

参数细节跑 `python3 scripts/image_api.py <子命令> -h`。

## 选哪个系列

用户没指定模型时，先问一句：

> 你有 OpenAI image 系列的接口吗？`gpt-image-2`、`gpt-image-2.5-flare`、`gpt-image-2.5-sunburst` 这一类。

没有就推荐百炼，原话照说：

> 没有的话建议用阿里云百炼的 qwen-image 系列，自己去百炼开通就行：实名认证后直接在控制台创建 API Key，不用信用卡，国内几分钟能拿到，新账号一般有免费额度。`qwen-image-3.0` 兼顾质量与速度，`qwen-image-2.1-turbo` 性价比最高，两者接口完全一样，换模型只改 `model`。

| | OpenAI image 系列 | 百炼 qwen-image 系列 |
|---|---|---|
| 典型模型 | `gpt-image-2`、`gpt-image-2.5-flare`、`gpt-image-2.5-sunburst` | `qwen-image-3.0-pro`、`qwen-image-3.0`、`qwen-image-2.1-pro`、`qwen-image-2.1-turbo` |
| 接入方式 | OpenAI Images 协议 | OpenAI 兼容、DashScope 同步、DashScope 异步，三种都支持 |
| 图生图 | `/images/edits` multipart | 兼容模式用 `generations` + `image` 字段；DashScope 用 `content` 数组 |
| 返回图片 | `b64_json`，另带宽高 | 只有 `url`，24 小时过期，不支持 b64 |
| 尺寸控制 | 请求值即输出值 | 官方协议同左；第三方兼容层可能失准，见「已知坑」 |

模型实测差异见 `references/models.md`。

## 两种协议怎么写

**OpenAI 兼容（P1）**：`POST {base}/images/generations`，JSON。
最小请求体 `{"model":"...","prompt":"...","size":"1024x1024","n":1}`。
`size` 用字母 `x`：`1024x1024`、`1024x1536`、`1536x1024`、`auto`。

**百炼（P2/P3）**：`POST .../api/v1/services/aigc/multimodal-generation/generation`。异步换成 `.../image-generation/generation` 并加 `X-DashScope-Async: enable` 头，拿 `task_id` 轮询 `/api/v1/tasks/{id}`。
`size` 用星号 `*`：`1024*1024`。文生图 `content` 只放一个 `{"text":"..."}`；图生图先放 `{"image":"..."}` 再放 `{"text":"..."}`，**只能有一个 text**。

两套写反了不一定报错，常见是被静默忽略然后给默认尺寸。`validate` 会先拦。

## 硬规则

1. 地址、Key、模型都不猜。缺哪项直接问，不要拿上一次的 Key 顶上。
2. Key 只走命令行参数、环境变量，或 `init` 保存的本地配置。**不写进请求 JSON、报告、最终回复**。脚本产出的 curl 里一律是 `$IMAGE_API_KEY`。
3. 默认 `n: 1`。用户没说数量就不批量。
4. 一次成功就停。追加生成、换模型重试都要用户明确说要。
5. 图生图必须验原图主体有没有进去，不能只看 HTTP 200。

## 图生图三条路

| 路径 | 命令 | 实测 |
|---|---|---|
| gpt 系 | `--proto openai-edit --image file.png` | 正常，尺寸精确 |
| qwen 官方写法 | `--proto openai`，`"image": "<url 或 data:...;base64,...>"` | 官方支持，但第三方兼容层可能直接丢弃这个字段 |
| qwen multipart | `--proto openai-edit` | 部分服务能出图，但 `size` 被忽略 |

qwen 的 `image` 只收公网 URL 或 `data:{MIME};base64,{data}`，**不收本地路径**；不能传 `null` 或空数组；张数上限 3.0 系 3 张、2.1 系 10 张。百炼协议更稳，比例和尺寸都可控。

## 已知坑

- **前台 120 秒超时会杀掉请求，但服务端往往已经出图并计费。** 一律放到 480 秒（脚本默认）。
- **兼容层会静默丢弃 qwen 的 `image` 字段。** 实测传橘猫出的是船和长椅，HTTP 全程 200。
- **qwen 走 `/images/edits` 时 `size` 失效**，锁 2K 档，比例跟输入图走。
- **`n>1` 可能只回一张**，另一张藏在 `metadata.output.choices[].message.content[]`。
- **`b64_json` 存在但是空字符串**，要判空值而不是判键是否存在。
- **`size:"auto"` 在兼容层可能 400**，那一层只认显式尺寸。
- **少写 `/v1` 会返回前端 HTML，状态码还是 200。** 先看响应体开头是 `{` 还是 `<`。
- **`model_not_found` 常以 503 返回**，不是 404，说明渠道没上这个模型。

## 错误码

| 码 | 处理 |
|---|---|
| 400 | 读 `error.message` 原文，按字段改，别整段重试 |
| 401 / 403 | Key 错、地域不对，让用户核对，不要重试 |
| 404 | 路径或模型名错，检查是否漏 `/v1` |
| 429 | 限流可退避一次；额度耗尽直接告知 |
| 503 | 上游故障或 `model_not_found`，别连续换模型重试 |

## 报告格式

鉴权是否通过（不显示 Key）、协议与模型、任务类型、HTTP 状态、返回类型、文件路径与真实尺寸、请求 JSON 和原始响应的位置。图生图要写是否确认原图主体被保留。失败就贴原始错误码和 `error.message`，不做美化。

## 目录结构

```
workbuddy-image/
├── SKILL.md
├── scripts/
│   └── image_api.py          九个子命令，零依赖
└── references/
    ├── models.md             模型清单与实测矩阵
    ├── openai-compatible.md  P1 全字段与响应结构
    └── dashscope.md          P2/P3 请求体、错误码
```

手写 curl 或 SDK 的等价写法，看 `references/openai-compatible.md` 和 `references/dashscope.md`；脚本只是省事。
