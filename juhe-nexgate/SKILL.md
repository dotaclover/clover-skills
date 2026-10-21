---
name: juhe-nexgate  
description: 调用聚合 Juhe Nexgate API，涵盖 GPT、Claude、DeepSeek、千问 Qwen、Seedance、Image-2 等系列。用于实时查询支持型号、按中文英文别名和任务解析模型、安全持久保存与复用 API Key，以及文本对话、图片生成编辑、视频生成下载；提供标准库 Python 辅助 CLI 和接口参考。
agent_created: true  
---

# 聚合 Juhe Nexgate API

通过统一服务地址和 API Key 使用文本、图片和视频接口。根据任务选择对应接口，并从当前 Key 的模型列表中选取完整型号 ID。

## 服务地址与鉴权

| 项目       | 值                                 |
| -------- | --------------------------------- |
| Base URL | `https://juhe.top`                |
| 鉴权       | `Authorization: Bearer <API Key>` |
| JSON 请求头 | `Content-Type: application/json`  |

## 必须先检查凭据，再选择任务与型号

使用 Python 3.9+ 标准库辅助 CLI `scripts/juhe.py`（下列命令从技能目录运行；其他目录使用脚本绝对路径）。不需要第三方依赖。

1. 首先执行 `python scripts/juhe.py auth status`。只读取配置状态，不发送请求、不输出 Key；`validated: false` 表示尚未联网验证。
2. 按非空 `JUHE_API_KEY` → 用户安全存储的顺序读取凭据。环境变量缺失不代表没有 Key。`source: saved` 时直接复用；不得重复询问。存储不可读时先排查 Windows 用户、文件损坏或权限，不当作缺失。
3. 仅在 `source: missing` 时引导用户在本机交互终端执行 `python scripts/juhe.py auth set`，通过 getpass 隐藏输入。不在聊天、命令参数、脚本、日志中提供明文 Key。此次维护或 mock 测试不需要 Key。禁止扫描无关私人文件寻找 Key。
4. 执行 `models` 实时 GET `/v1/models`；再通过 `resolve` 将用户任务和中文/英文别名与实时列表相交。必须明确任务，不把千问聊天型号用于绘图。
5. 只有一个已知候选时返回 `selected`；多个候选请确认完整 ID，不擅自声称某型号最新、最强或最便宜。未知 ID 标注能力未知，不按名称猜能力、参数或接口。能力依据是随附参考，实时列表只证明可见，不证明健康度或能力。

```bash
python scripts/juhe.py auth status
python scripts/juhe.py models
python scripts/juhe.py resolve 千问 --task 绘图
python scripts/juhe.py resolve qwen --task chat
python scripts/juhe.py resolve 万相 --task 视频
python scripts/juhe.py resolve gpt-image-2 --task 图片编辑
```

千问/通义千问/qwen + 绘图仅匹配已知且实时可见的 `qwen-image-3.0`，不会落到 `qwen3.*` 聊天型号；若新增 `qwen-image-*` 未登记，先查证服务文档再补充映射。别名和任务明细见 [模型清单](references/models.md)。

### 凭据存储与安全边界

- Windows 保存到 `%LOCALAPPDATA%/juhe-nexgate/credential.json`，使用当前用户级 DPAPI 密文（不设置机器级标志）；只能由同一用户在兼容环境解密。环境变量优先且不会自动落盘；`auth set` 只保存交互输入，不打印 Key 或片段。不因网络故障删除或重设 Key。
- 非 Windows 保存到 `${XDG_CONFIG_HOME:-~/.config}/juhe-nexgate/credential.json`，目录0700、文件0600并检查属主和权限。此模式为权限保护的明文，不是加密；需要磁盘保密时使用系统加密或仅提供环境变量。Windows DPAPI 不能防御同一已登录用户下的恶意程序。
- 禁止将 Key 写入技能目录、仓库、打包文件或示例。不要把 `LOCALAPPDATA`、`XDG_CONFIG_HOME` 指向技能或仓库。已有技能内配置仅检查是否有可迁移凭据，不展示内容，不自动迁移或删除；经用户确认后通过安全流程处理。
- CLI 没有 `--key`、打印/导出 Key 或任意鉴权请求命令。不通过命令行头部传入真实 Key。新调用脚本应在进程内 `from juhe import credential; key, source = credential()` 获取，随后在内存中构造鉴权头；不要把安全存储里的 Key 导出给 shell。
- 下文及参考文件中的 curl 仅用于说明请求格式，要求用户已自行配置环境变量。代理实际调用应使用进程内读取，避免 curl 参数展开泄露 Key；不要为运行示例再次询问或重新输入已保存凭据。

### 缓存、失效与错误

- `models`、`resolve` 默认实时查询。显式 `--cached` 才允许使用15分钟内、同服务地址和同凭据的缓存；缓存存储在上述用户配置目录的 `models-cache.json`，不保存原始 Key，仅保存隔离哈希、时间和型号 ID。
- 运行 `python scripts/juhe.py cache-clear` 清缓存。换 Key、换 Base URL、缓存过期或损坏均重新拉取；`auth set` 和 HTTP 401 清缓存。网络失败不自动使用过期缓存，不声称旧列表实时有效。
- `unauthorized` 专指 HTTP 401，先检查凭据来源，特别是旧环境变量覆盖了新保存值。`network` 为网络/TLS/超时，不索要新 Key；`http` 保留状态码区分403、429和5xx；`response` 为无效列表；`storage` 为本地安全存储错误。错误不输出响应正文、请求头或原始异常。
- 服务地址默认 `https://juhe.top`；允许通过 `JUHE_BASE_URL` 或 `--base-url` 指定可信 HTTPS 根地址（不带 `/v1`）。拒绝重定向，避免 Bearer Key 泄露到其他域名。自定义地址会收到 Key，仅使用用户明确授权的可信服务。

## 按任务选择接口

| 任务与系列                     | 入口                                                    | 调用说明                                                |
| ------------------------- | ----------------------------------------------------- | --------------------------------------------------- |
| GPT、Claude、DeepSeek 等文本对话 | `POST /v1/chat/completions`                           | [文本请求与流式示例](references/text.md)                     |
| GPT Responses             | `POST /v1/responses`                                  | [Responses 示例](references/text.md#3-gpt-responses)  |
| Claude Messages           | `POST /v1/messages`                                   | [Messages 示例](references/text.md#4-claude-messages) |
| Gemini 原生文本请求             | `POST /v1beta/models/{model}:generateContent`         | [Gemini 示例](references/text.md#5-gemini-原生格式)       |
| Image-2 等图片生成与编辑          | `POST /v1/images/generations`、`POST /v1/images/edits` | [图片请求与保存结果](references/images.md)                   |
| Seedance 视频               | 方舟格式或 OpenAI Video 格式                                 | [Seedance 参数与示例](references/seedance.md)            |
| 其他视频型号                    | `POST /v1/videos`                                     | [其他视频请求](references/other-video.md)                 |

型号与请求入口见 [模型清单](references/models.md)，错误原因与处理方法见 [常见报错与处理](references/troubleshooting.md)。型号与可用性会随时间、Key 权限、额度及服务状态变化，以当前 `/v1/models` 和请求响应为准。

## 文本请求快速开始

```bash
curl --silent --show-error --fail-with-body \
  "$JUHE_BASE_URL/v1/chat/completions" \
  -H "Authorization: Bearer $JUHE_API_KEY" \
  -H 'Content-Type: application/json' \
  --data '{
    "model": "gpt-6.1-sol",
    "messages": [{"role": "user", "content": "用三句话介绍太阳能发电。"}],
    "max_tokens": 512,
    "stream": false
  }'
```

文本从 `choices[0].message.content` 读取。调用其他系列时，阅读相应参考文件，按其格式提交。

## 调用要点

- 请求地址使用 `https://juhe.top`；示例中的 `JUHE_BASE_URL` 不包含 `/v1`，按示例拼接路径。
- `GET /v1/models` 返回的 `data[].id` 是请求所用的型号名称；按文本、图片、视频任务选用对应接口。
- 文本流式请求读取 SSE；图片响应可能是 Base64 或 URL；视频创建返回任务 ID，须查询到完成后下载。
- 视频两种创建格式任选一种，同一需求只提交一次。超时或暂时查询失败时，先核对已有任务。
- 发生错误时读取响应中的 `error`。`401` 检查 Key，`400` 检查参数，`403` 检查权限，`429` 根据具体错误区分限流与额度问题；`5xx` 或超时保留错误信息后再处理。
- 图片、视频等长耗时任务必须显式设超时：图片 `--max-time 180`–`300`，视频创建后用任务 ID 轮询。不要依赖默认无限等待。
- `/v1/models` 能列出型号不代表该型号当前可用。某型号超时或返回 `524` 时，先用文本型号发一条最小请求探活，再换同系列型号验证，不要持续加大等待时间；判定流程见 [常见报错与处理](references/troubleshooting.md)。
