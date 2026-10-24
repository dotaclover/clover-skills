---
name: baidu-api-dev
description: 百度 API 开发技能：按需整合旧 VOD、新 VOD、千帆 Qianfan 与百度 AI 网关 Seedance 的接口、模型、new-api 接入和安全测试；保持凭据、端点与协议独立，不执行未授权外部写入或收费请求。
agent_created: true
---

# 百度 API 开发

本技能是合并后的当前入口，面向接口开发、协议核对、最小离线 CLI 验证和按需 new-api 配置说明。旧技能正文仅作为历史资料保存在 `references/legacy-*.md`，不是当前入口；当前接口与操作应以本文件和按需加载的 references 为准。

## 接入总表

| 接入 | 用途 | Base URL 环境变量 | 主要端点 | 鉴权/凭据边界 |
|---|---|---|---|---|
| 旧 VOD | OpenAI 兼容聊天；另有独立 VOD 视频插件 | `BAIDU_VOD_URL` / `BAIDU_VOD_KEY` | `POST {base}/v1/chat/completions` | 仅使用旧 VOD Key；模型通常手工配置 |
| 新 VOD | OpenAI 兼容聊天 | `BAIDU_NEWVOD_URL` / `BAIDU_NEWVOD_KEY` | `POST {base}/v1/chat/completions` | 仅使用新 VOD Key；不要追加旧 VOD 路径 |
| 千帆 QF | V2 聊天、模型目录、向量、图像、重排序及 FireSeries 视频 | `BAIDU_QF_URL` / `BAIDU_QF_KEY` | `GET /v1/models`；`POST /v2/chat/completions`；视频 `/beta/video/generations/qianfan-video/fireseries` | 仅使用 QF Key；`token|appid` 需由适配器拆分 |
| 百度 AI 网关 | 原生 Seedance 异步视频、素材 Action、真人 H5 | `BAIDU_AI_URL` / `BAIDU_AI_KEY` | `POST /api/v3/contents/generations/tasks`；查询 `GET /api/v3/contents/generations/tasks/{task_id}`；Action 使用 `/?Action=...&Version=2024-01-01` | 仅使用 AI 网关 Bearer Key；不使用火山 AK/SK |

四套 Base URL、Key、端点和模型命名不得互换。QF FireSeries 使用 `S2.0` 等短名；AI 网关 Seedance 使用完整模型名。官方 Ark 协议参考保持原样，不在本技能中改动或代替百度 AI 网关配置。

## 按需参考

- VOD 接口与 cURL：[`references/vod-api.md`](references/vod-api.md)
- VOD 与四类接入模型/端点边界：[`references/vod-models.md`](references/vod-models.md)
- Qianfan 接口与 new-api 渠道：[`references/qianfan-api.md`](references/qianfan-api.md)
- Qianfan 模型：[`references/qianfan-models.md`](references/qianfan-models.md)
- Qianfan FireSeries Seedance：[`references/qianfan-seedance.md`](references/qianfan-seedance.md)
- AI 网关 Seedance 接口、素材和 H5：[`references/seedance-api.md`](references/seedance-api.md)
- AI 网关脱敏实测与边界：[`references/seedance-verification.md`](references/seedance-verification.md)
- new-api 渠道与协议边界已合并进 `qianfan-api.md`；不要把客户技能、专家包或外部 Ark 配置当作本技能入口。
- `legacy-*.md` 仅用于历史追溯，不作为当前引用目标，也不应触发重复技能发现。

## 最小 CLI

脚本使用 Python 标准库；`--help` 仅解析参数，不发送网络请求。只读子命令（如 models、查询任务和列表）会访问网络；写入或计费子命令分别需要对应的 `--send`、`--allow-write` 或 `--allow-charge`，不是每条命令都需要全部开关。

```powershell
# 仅离线查看帮助
python scripts/chat_smoke.py --help
python scripts/qianfan.py --help
python scripts/seedance.py --help

# 单次聊天：明确允许可能计费的外部请求
python scripts/chat_smoke.py --provider old --model glm-5.3 --send
python scripts/qianfan.py chat --model glm-5.3 --send

# 只读模型目录仍需配置 QF 凭据，会发送外部 GET；按用户要求单独执行
python scripts/qianfan.py models

# AI 网关素材组只读查询：需要联网授权，不需要 --allow-write
python scripts/seedance.py action ListAssetGroups --body '{"ProjectName":"default","Filter":{"GroupType":"AIGC"},"PageNumber":1,"PageSize":10}'

# 收费视频创建：必须同时有明确付费授权和 --allow-charge
python scripts/seedance.py video-create --body-file body.json --allow-charge

# 聊天批量探测：脚本默认拒绝多模型批量执行，只有明确传 -AllowBatch 才允许
& .\scripts\test-baidu-provider.ps1 -Provider Vod -AllowBatch
```

### 语义与安全边界

- `--send`：允许对应脚本发送一条可能计费的聊天请求；没有它不得发送。
- `--allow-write`：允许当前用户已明确授权的外部写操作，例如素材修改/删除或 H5 创建；不代表允许收费视频生成。
- `--allow-charge`：额外确认收费视频创建；没有它不得提交视频任务。
- 批量测试必须由用户明确授予批量授权；不因环境变量存在、模型列表存在或 `All` 默认值而执行。PowerShell 批测使用 `-AllowBatch`。
- 计费、外部写入、删除、H5 创建、真人扫码/同意和收费成片都不是默认操作。不得把任务提交成功当作成片完成，也不得把 H5 创建当作真人授权完成。
- 不打印或写入 Key、Token、Cookie、签名媒体 URL；AI 网关脚本仅允许显式指定的新本机私有输出文件保存一次原始响应。
- 不执行真实网络、批量测试或收费操作，除非用户在当前请求中给出相应的明确授权。当前合并仅做静态检查和离线 `--help` 验证。

## new-api 边界

- 旧 VOD、新 VOD 使用 OpenAI 兼容聊天路径，但分别配置渠道和 Key。
- QF 使用 Baidu V2 渠道；聊天路径为 `/v2/chat/completions`，FireSeries 视频走 QF 专用路径。
- AI 网关不是聊天渠道，也不是 QF；Seedance 插件按其渠道类型发送原生任务协议或进入 QF 分支。
- 只有当前真实直连成功的模型才可加入渠道模型列表；模型目录可见不代表调用权限。
- `z-image` 不在本技能声明支持范围内，不得填入百度渠道。
- 新增价格必须以供应商当前官方价格为事实来源，明确币种、计价单位、输入/输出和缓存分类；未核验价格不得猜测。
