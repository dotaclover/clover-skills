---
name: juhe-nexgate
description: 接入已部署的 Juhe Nexgate 聚合 API，管理客户端凭据、查询和选择模型，调用文本、同步/异步图片、视频及 Seedance 素材接口。用于用户应用集成、生成和任务查询；修改网关/账号池源码或部署使用 juhe-nexgate-dev。
---

# Juhe Nexgate API 接入

默认服务根地址 `https://juhe.top`，鉴权 `Authorization: Bearer <API Key>`，JSON 请求带 `Content-Type: application/json`。Base URL 不带 /v1；OpenAI SDK 的 base_url 通常要追加 /v1，避免遗漏或重复。用户提供其他可信服务时按其地址使用，确认该地址有权接收当前 Key。

## 先区分任务

- **仅写集成代码/解释接口**：直接使用环境变量占位符和参考，不索要真实 Key、不发付费请求。
- **创建新内容**：读取已有凭据，必要时用 models/resolve 从当前可见型号选型，再按已授权需求提交。只提交所需数量，不附带其他付费“探活”。
- **查询既有任务/保存已有结果**：直接使用原服务、原 Token 和任务 ID，不要求先访问 models、不创建新任务。
- **排查错误**：读 HTTP 状态、任务状态、request_id；按 [troubleshooting](references/troubleshooting.md) 区分认证、部署、输入和执行不确定性。

模型列表只证明当前 Token 可见，不证明上游健康、全部参数兼容或异步接口已部署。尤其图片异步是网关扩展，需要服务方部署并启用；本技能更新不代表默认公网已上线。

## 凭据与 CLI

使用 Python 3.9+ 标准库工具 `scripts/juhe.py`，以下命令在技能目录运行，其他目录用绝对脚本路径：

```bash
python scripts/juhe.py auth status
python scripts/juhe.py models
python scripts/juhe.py resolve 千问 --task 绘图
python scripts/juhe.py auth set
python scripts/juhe.py auth clear
```

实际调用前执行 auth status：configured=true 直接复用；缺失时再请用户配置 JUHE_API_KEY，或在可交互终端 auth set 隐藏输入。若用户希望持久保存，可用 auth set；自动化可通过 stdin 调用 auth set --stdin，不把真实 Key 写进 shell 命令字面量、参数、代码或工具输出。不要求用户把 Key 发进聊天；用户已提供时不复述或反复索取。

环境变量 JUHE_API_KEY 优先于已保存值，且不会自动落盘。保存后核对 saved_exists 和 configured，source 仍可能是 environment，这不表示保存失败。auth clear 删除保存值和缓存，不撤销服务端 Key，也不清除进程环境变量。

- Windows：用户目录下 DPAPI 密文；非 Windows：0700/0600 权限保护的明文，不能宣称加密。凭据不能写入技能、仓库或交付包。
- 进程内集成可 `from juhe import credential; key, source = credential()`，不导出明文到 shell。命令行不提供 --key。
- 换服务域名前确认用户授权，不把已有 Key 自动发送到陌生主机。CLI 只接受 HTTPS 根地址且拒绝重定向。
- 401 检查来源和覆盖关系；网络/超时不是凭据失效，不删除 Key、不反复索取。缓存只在显式 --cached 时使用，有效 15 分钟、按服务及凭据隔离。
- models/resolve 在创建前需要选型时使用；用户指定完整有效 ID 时尊重选择。多个候选且选择影响结果时询问，不猜“最新/最便宜”；未知能力先核实。

## 接口路由

| 任务 | 入口 / 参考 |
| --- | --- |
| Chat、Responses、Claude Messages、Gemini | [text.md](references/text.md) |
| 同步图片生成/编辑、结果解码 | [images.md](references/images.md) |
| 图片提交后立即拿 task_id，稍后查询 | [async-images.md](references/async-images.md)；CLI images submit/get |
| Seedance 两种视频协议 | [seedance.md](references/seedance.md) |
| 其他视频 | [other-video.md](references/other-video.md) |
| 素材、分组、真人认证 | [material.md](references/material.md)；CLI material |
| 型号与已知能力 | [models.md](references/models.md) |
| 错误、超时、重试 | [troubleshooting.md](references/troubleshooting.md) |
| 历史验证范围 | [verification.md](references/verification.md) |

文本通常使用 POST /v1/chat/completions，读取 choices[0].message.content；SSE 按事件读取，检查结束原因及 usage。POST /v1/responses 并不代表支持 background=true 和 GET Responses 查询，未确认部署能力前不承诺。

## 异步图片快速接入

在技能目录外的工作目录创建 UTF-8 `image-request.json`（不含 Key）。下面用脚本绝对路径调用；将 `/path/to` 换成实际安装位置：

```json
{"model":"gpt-image-2","prompt":"一只在窗边的猫","n":1,"size":"1024x1024"}
```

```bash
python /path/to/juhe-nexgate/scripts/juhe.py images submit --request-file image-request.json --idempotency-key order-001 --output image-task.json
python /path/to/juhe-nexgate/scripts/juhe.py images get --id img_RETURNED_ID --output image-result.json
```

submit 返回服务端生成的 task_id；Idempotency-Key 是客户端防重复标识，两者不同。保存原请求文件、幂等 key、服务地址及原 Token 的配置来源，勿记录 Token 明文。CLI 每次只发一个请求，不自动轮询或重发；GET 输出文件包含完整 result，终端仅显示摘要。按状态每 2–5 秒查询，设置总等待期限，期限到达保留任务 ID，不能当作服务端取消。

## 调用与交付边界

- 同步图片超时/5xx 不证明未生成；不要自动换型号、重提或转异步。异步提交网络中断时，只能原 Token、同一幂等 key、完全相同请求字节恢复；已有 task_id 只 GET。needs_review 停止自动处理并核账。
- 视频两种创建格式任选一种，只提交一次；按该协议响应里的 ID 和状态查询，不把图片 task_id 与视频 id/查询路径混用。
- 图片结果可能是 b64_json 或临时 URL，保存完整响应并解码/下载；媒体下载不附带网关 Bearer。失败先取原结果，不能自动重新生成。完整 base64 不打印到终端。
- 素材先到 Active，再用 result.URL 或经文档确认的 asset:// 引用；真人认证必须由本人完成 H5，普通 AIGC 不代表真人授权，详见 material。
- 交付可运行的代码/命令、所用模型及接口、任务 ID/状态、结果文件与未验证项。仅配置检查不能说生成成功，HTTP 202/200 也不等于任务 completed。
