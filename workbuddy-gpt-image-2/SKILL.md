---
name: workbuddy-gpt-image-2
description: 用`GPT_IMG_URL`/`GPT_IMG_KEY`调用`gpt-image-2`文生图，凭据优先读电脑环境变量，缺失时向用户索要并存到`~/.workbuddy/gpt-img-auth.json`。适用于用户要用gpt-image-2出图、做海报或竖图的场景。
agent_created: true
---

# gpt-image-2出图

只做一件事：调`gpt-image-2`文生图，落盘并报真实尺寸。零第三方依赖，脚本只调系统curl。原`aigc-image`技能不动。

## 凭据（每次先做）

```bash
python scripts/gpt_img.py auth
```

- 返回`ok: true`：地址和Key已从`GPT_IMG_URL`/`GPT_IMG_KEY`读到，并缓存到`~/.workbuddy/gpt-img-auth.json`，直接出图。
- 返回`missing`：**向用户索要缺的那几项**，不猜、不拿别的技能的Key顶。拿到后写入缓存：

```bash
python scripts/gpt_img.py auth --url <地址> --key <Key>
```

- 查看当前状态（Key打码）：`python scripts/gpt_img.py auth --show`

读取顺序：命令行 > 进程环境变量 > Windows用户级环境变量 > Windows系统级环境变量 > auth文件。Windows用户级/系统级变量直接从注册表读，进程没继承也能拿到。

环境变量只给域名时自动补`/v1`；给的是完整路径就原样用。auth文件是明文，别提交Git。

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
| `--url` / `--key` | — | 临时覆盖，仅本次生效 |

产物：`request.json`、`response.json`、`image-01.png`。报告含HTTP状态、真实宽高、尺寸是否对得上。

## 硬规则

1. Key不出现在回复、报告、请求JSON、日志里。
2. 模型固定`gpt-image-2`，不换模型重试。
3. 一次成功就停。失败先贴原始错误，未经用户明确要求不重发——会重复计费。
4. 超时480秒。别用120秒前台超时掐断，服务端可能已经出图并计费。
5. 中文大字别让模型写，出图后用PIL叠字。

## 已知坑

- 这层网关按UA拦Python urllib（403 / error 1010），所以走curl加浏览器UA。
- 必须`--noproxy '*'`：本机代理会让4K大图（十几MB）传不完，看着像超时，其实服务端已经200。
- 响应一律`-o`落文件，不走stdout管道。
- `4096x4096`不支持；`3840x2160` / `2160x3840`可用。

## 目录

```
clover-gpt-image-2/
├── SKILL.md
└── scripts/gpt_img.py
```
