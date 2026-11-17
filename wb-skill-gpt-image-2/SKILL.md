---
name: wb-skill-gpt-image-2
display_name: GPT Image 2出图
display_name_en: GPT Image 2 Generator
description: 用自己的接口地址和Key调用gpt-image-2出图，支持文生图与参考图图生图。凭据优先读GPT_IMG_URL和GPT_IMG_KEY环境变量，缺失时向用户索要并存到本地。脚本自带离线自检、参数校验、请求体构造、尺寸模板，不需要Key也能验证可用。
description_zh: 用环境变量里的自有接口生成gpt-image-2图片，支持文生图和参考图图生图，2K方图实测尺寸精确。自带离线自检与尺寸模板，产物落在调用目录。
description_en: Generate gpt-image-2 images through your own OpenAI-compatible endpoint using GPT_IMG_URL and GPT_IMG_KEY. Supports text-to-image and reference-image editing with verified 2048x2048 output. Built-in offline self-test, validation and size presets.
examples_zh:
  - '用我的接口出一张2K海报'
  - '照这张脸生成一组头像'
  - '把这张图改成短发二次元风'
examples_en:
  - 'Generate a 2K poster through my image API'
  - 'Make a set of avatars from this face photo'
  - 'Turn this photo into a short-hair anime avatar'
version: 1.0.1
author: 独立开发者
agent_created: true
---

# GPT Image 2出图

只做一件事：调`gpt-image-2`出图，落盘并报真实尺寸。零第三方依赖，Python 3.8+，联网部分只调系统curl。所有离线命令不需要网络和Key，随时可跑。

## 快速开始

```bash
# 1. 先自检，确认脚本可用（不需要网络和Key）
python scripts/gpt_img.py self-test

# 2. 校验参数、构造请求体（不发请求、不花钱）
python scripts/gpt_img.py validate --size 1024x1536
python scripts/gpt_img.py build --prompt "一只橘猫" --size 1024x1536 --out req.json

# 3. 存一次凭据，之后不用每次传
python scripts/gpt_img.py auth

# 4. 出图
python scripts/gpt_img.py generate --prompt "一只橘猫坐在窗台上" --size 1024x1536
```

Windows上把`python`换成实际解释器；脚本本身跨平台。

## 命令速查

| 子命令 | 要Key | 干什么 |
|---|---|---|
| `self-test` | 否 | 全离线自检，28项，跑完必全PASS |
| `presets` | 否 | 常用尺寸模板：公众号、小红书、海报、头像 |
| `validate` | 否 | 校验size写法、像素范围、宽高比、n上限 |
| `build` | 否 | 构造请求体JSON，不发请求；可交给联网流程 |
| `size` | 否 | 读PNG/JPEG真实宽高 |
| `auth` | 否 | 读环境变量并缓存；`--show`查看状态（Key打码） |
| `generate` | 是 | 文生图；给`--image`走图生图 |

## 常用尺寸模板（内容由用户补）

模板只给尺寸、比例和风格骨架，具体画什么由用户说，提示词里留`【用户补充的内容】`占位。

| 场景 | id | 尺寸 | 比例 | 适合 |
|---|---|---|---|---|
| 公众号封面首图 | `wechat-cover` | 1536x1024 | 3:2 | 左侧留白放标题 |
| 公众号正文配图 | `wechat-inline` | 1024x1024 | 1:1 | 扁平插画，多图并排不亏 |
| 小红书封面 | `xhs-cover` | 1024x1536 | 2:3 | 上方留标题区 |
| 小红书实拍感 | `xhs-photo` | 1024x1024 | 1:1 | 要「不像AI生成」用这个 |
| 竖版海报 | `poster` | 1024x1536 | 2:3 | 留标题与卖点位 |
| 头像 / 人物图 | `avatar` | 1024x1024 | 1:1 | 半身正面，留裁切余量 |

```bash
python scripts/gpt_img.py presets                  # 看全部
python scripts/gpt_img.py presets --id xhs-cover   # 看完整提示词
python scripts/gpt_img.py presets --scene 公众号    # 按场景过滤
```

三条提前说清，别等交付后再扯：

- 公众号官方封面是**2.35:1**，接口不直接支持。按1536x1024出图再裁成900x383。
- 小红书主流**3:4**，接口只给2:3，出图后上下各裁一点就接近。
- **文字别让模型直接写**，小字容易糊，出图后用PIL自己加。

## 凭据（联网出图前先做）

```bash
python scripts/gpt_img.py auth
```

- 返回`ok: true`：地址和Key已从`GPT_IMG_URL`/`GPT_IMG_KEY`读到，并缓存到`~/.workbuddy/gpt-img-auth.json`，直接出图。
- 返回`missing`：**向用户索要缺的那几项**，不猜、不拿别的技能的Key顶。拿到后写入缓存：

```bash
python scripts/gpt_img.py auth --url <地址> --key <Key>
```

- 查看当前状态（Key打码）：`python scripts/gpt_img.py auth --show`

读取顺序：命令行 > 进程环境变量 > Windows用户级环境变量 > Windows系统级环境变量 > auth文件。Windows用户级/系统级变量直接从注册表读，进程没继承也能拿到。环境变量只给域名时自动补`/v1`；给的是完整路径就原样用。auth文件是明文，别提交Git。

## 出图

```bash
python scripts/gpt_img.py generate --prompt "一只橘猫坐在窗台上" --size 1024x1536
```

| 参数 | 默认 | 说明 |
|---|---|---|
| `--prompt` | 必填 | 画面描述 |
| `--size` | `1024x1024` | 字母x，如`1536x1024`、`3840x2160`；`auto`交给服务端 |
| `--n` | `1` | 张数，多图成倍计费 |
| `--out-dir` | `./gpt-image-2-out` | 产物落在调用目录 |
| `--image` | — | 参考图本地路径；给了就走`/images/edits`图生图 |
| `--url` / `--key` | — | 临时覆盖，仅本次生效 |

`generate`会先跑`validate`，参数有问题直接拦，不会白花钱。产物：`request.json`、`response.json`、`image-01.png`。带参考图时多一个`request.bin`（multipart原文）。报告含HTTP状态、`mode`、真实宽高、尺寸是否对得上。

## 参考图

```bash
python scripts/gpt_img.py generate --prompt "参考所附人物的五官和发型，做一组头像" \
  --image "C:/path/face.jpg" --size 2048x2048
```

参考图走`/images/edits` multipart，字段是`image`+`model`/`prompt`/`size`/`n`，中文prompt按UTF-8编码。实测主体能进去（脸型、眼镜、发型保留），尺寸精确。**交付前必须看图确认参考主体真的进去了，不能只看HTTP 200**——兼容层有静默丢图的前科。图生图改发型这类局部特征时，兼容层会强保留参考图的原发型，prompt压不过去；把参考图对应区域涂掉再传，一次就成。

## 硬规则

1. Key不出现在回复、报告、请求JSON、日志里。构造请求体一律用`build`，输出不含Key。
2. 模型固定`gpt-image-2`，不换模型重试。
3. 默认`n: 1`。用户没说数量就不批量。
4. 一次成功就停。失败先贴原始错误，未经用户明确要求不重发——会重复计费。
5. 超时480秒。别用120秒前台超时掐断，服务端可能已经出图并计费。
6. 中文大字别让模型写，出图后用PIL叠字。
7. 图生图必须看图确认参考主体进去了，HTTP 200不算成功。

## 已知坑

- 这层网关按UA拦Python urllib（403 / error 1010），所以走curl加浏览器UA。
- 必须`--noproxy '*'`：本机代理会让4K大图（十几MB）传不完，看着像超时，其实服务端已经200。
- 响应一律`-o`落文件，不走stdout管道。
- `4096x4096`不支持；`3840x2160` / `2160x3840`可用。
- 接口地址漏`/v1`会返回前端HTML，状态码还是200；脚本会检查响应体是不是`{`开头。
- 兼容层可能静默忽略不支持的字段或改尺寸，`size`对不上会写进报告的`size_mismatch`，别只信请求值。

## 报告格式

鉴权状态（不显示Key，只报来源）、`mode`、模型、HTTP状态、文件路径与真实尺寸、请求JSON和原始响应的位置。图生图要写是否确认参考主体被保留。失败就贴原始错误码和`error.message`，不做美化。

## 目录

```
clover-gpt-image-2/
├── SKILL.md
└── scripts/gpt_img.py
```
