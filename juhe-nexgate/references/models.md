# 模型清单与请求入口

以下列出各系列的型号及请求入口，供选择请求格式时参考。型号可能新增或调整，调用前使用 `GET /v1/models` 获取当前 Key 可见的 `data[].id`。

模型列表不代表实时健康度或请求一定成功；可用性受权限、额度、限流和服务状态影响。遇到错误时按 [常见报错与处理](troubleshooting.md) 排查。

## 实时列表与任务解析

运行 `python scripts/juhe.py models` 实时获取当前凭据的可见型号。运行 `python scripts/juhe.py resolve <别名或完整ID> --task <任务>` 与已知映射相交；显式 `--cached` 可复用15分钟缓存。输出中的 `capability_source: bundled-references` 指本文及其他随附参考，不代表刚查询到能力；`unknown` 表示未登记能力。新型号必须核实服务文档后才更新 `scripts/juhe.py` 的精确 ID 映射，不用前缀猜能力。

| 中文/英文别名 | 任务区分 |
|---|---|
| 千问、通义千问、通义、qwen | chat 对应已知 qwen3.*；image 对应已知 qwen-image-3.0 |
| 深度求索、deepseek | chat |
| 智谱、glm；月之暗面、kimi | chat |
| gpt、claude、gemini | chat |
| image2、image 2、image-2、gpt image | image 或 image-edit |
| 万相、通义万相、wan | image、image-edit、video 分开筛选 |
| 豆包、即梦、seedance | video；参考输入以具体型号的已登记任务为准；别名不是完整产品能力声明 |
| 快乐马、happyhorse | video、image-to-video、reference-image-to-video、video-edit 分开筛选 |

任务别名：聊天/文本→chat；绘图/生图/文生图→image；改图/图片编辑→image-edit；视频/文生视频→video；图生视频→image-to-video；参考图生视频→reference-image-to-video；参考视频→reference-video；视频编辑→video-edit。任务必须显式指定。未知完整 ID 可以被列出但不会自动调用；系列查询只推荐已登记能力且实时可见的候选。多个候选不擅自排序为质量或价格推荐。

## GPT

| `model` | 请求入口 |
|---|---|
| `gpt-5.6-luna` | `/v1/chat/completions` |
| `gpt-5.6-sol` | `/v1/chat/completions` |
| `gpt-5.6-terra` | `/v1/chat/completions` |
| `gpt-6-astra` | `/v1/chat/completions` |
| `gpt-6-luna` | `/v1/chat/completions` |
| `gpt-6-sol` | `/v1/chat/completions` |
| `gpt-6.1-sol` | `/v1/chat/completions` |

Responses 和流式输出的请求格式见 [文本接口](text.md)。

## Claude

| `model` | 请求入口 |
|---|---|
| `claude-fable-5-1` | `/v1/chat/completions` |
| `claude-opus-4-8` | `/v1/chat/completions` |
| `claude-opus-5-5` | `/v1/chat/completions` |

Messages 的参数和流式读取方式见 [文本接口](text.md#4-claude-messages)。

## DeepSeek

| `model` | 请求入口 |
|---|---|
| `deepseek-v4-flash` | `/v1/chat/completions` |
| `deepseek-v4-pro` | `/v1/chat/completions` |
| `deepseek-v4.1-flash` | `/v1/chat/completions` |

## Image-2

| `model` | 请求入口 |
|---|---|
| `gpt-image-2` | `/v1/images/generations` |
| `gpt-image-2.5-flare` | `/v1/images/generations` |
| `gpt-image-2.5-sunburst` | `/v1/images/generations` |

图片生成与 multipart 编辑请求见 [图片接口](images.md)。

## Seedance

| `model` | 请求入口 |
|---|---|
| `doubao-seedance-2-0-260128` | `/api/v3/contents/generations/tasks` |
| `doubao-seedance-2-0-fast-260128` | `/api/v3/contents/generations/tasks` |
| `doubao-seedance-2-0-mini-260615` | `/v1/videos` |
| `doubao-seedance-2-5-260628` | `/v1/videos` |

方舟格式和 OpenAI Video 格式的参数见 [Seedance 请求](seedance.md)。

## 其他文本型号

| `model` | 请求入口 |
|---|---|
| `gemini-3.5-flash` | `/v1/chat/completions` |
| `gemini-3.6-flash` | `/v1/chat/completions` |
| `glm-5.2` | `/v1/chat/completions` |
| `glm-5.3` | `/v1/chat/completions` |
| `kimi-k3` | `/v1/chat/completions` |
| `qwen3.5-flash` | `/v1/chat/completions` |
| `qwen3.5-plus` | `/v1/chat/completions` |
| `qwen3.6-flash` | `/v1/chat/completions` |
| `qwen3.6-plus` | `/v1/chat/completions` |
| `qwen3.8-27b` | `/v1/chat/completions` |
| `qwen3.8-flash` | `/v1/chat/completions` |
| `qwen3.8-max` | `/v1/chat/completions` |

Gemini 原生格式与 Messages 示例见 [文本接口](text.md)，接口与参数支持取决于所选型号。

## 其他图片型号

| `model` | 请求入口 |
|---|---|
| `qwen-image-3.0` | `/v1/images/generations` |
| `wan2.6-image` | `/v1/images/generations` |
| `wan2.7-image-pro` | `/v1/images/generations` |

`wan2.6-image` 使用参考图片生成或图片编辑格式，见 [图片接口](images.md)。

## 其他视频型号

| `model` | 请求入口 |
|---|---|
| `happyhorse-1.0-video-edit` | `/v1/videos` |
| `happyhorse-1.1-i2v` | `/v1/videos` |
| `happyhorse-1.1-r2v` | `/v1/videos` |
| `happyhorse-1.1-t2v` | `/v1/videos` |
| `wan3.0-video-prime` | `/v1/videos` |

这些型号使用视频接口，参考图片和源视频的输入格式见 [其他视频请求](other-video.md)。
