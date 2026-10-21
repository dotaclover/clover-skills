---
name: seedance-bd
description: 接入和实测百度 AI 网关的 Seedance 视频任务、素材与真人 H5 授权；使用百度 Bearer API Key，不适用于千帆 QF、旧/新 VOD或火山官方 AK/SK。
agent_created: true
---

# 百度 AI 网关 Seedance

直接连接 `BAIDU_AI_URL`（通常为 `https://ai-gateway.baidubce.com`），凭据为 `BAIDU_AI_KEY`。不要替换为客户网关地址，不要混用 `BAIDU_QF_KEY`、VOD Key、火山 API Key 或火山 AK/SK。

## 工作流

1. 读 [接口、参数和 curl](references/api.md)，明确视频任务、普通 AIGC 素材和真人授权是不同流程。
2. 真实请求前读 [实测记录与边界](references/verification.md)。历史成功不代表当前账号、模型或其他供应商已通过。
3. 使用标准库脚本做当前账号的请求；默认输出脱敏响应。脚本不自动读取 `.env`，只有显式指定 `--env-file` 才读取，已有进程环境优先。

```powershell
python scripts/seedance.py --env-file C:/path/to/.env action ListAssetGroups --body '{"ProjectName":"default","Filter":{"GroupType":"LivenessFace"},"PageNumber":1,"PageSize":10}'
python scripts/seedance.py --env-file C:/path/to/.env smoke --allow-write --callback-url https://example.com/seedance/callback
```

`smoke` 只做列表查询、临时 AIGC 组创建/改名/查询/删除、一次 H5 创建和一次未扫码结果查询，不提交视频，不进行真人同意；只清理本次创建的临时组。H5/Token不写报告或终端。

## 必须保持的边界

- 视频用 `/api/v3/contents/generations/tasks`；素材与 H5 用 `/?Action=...&Version=2024-01-01`，均为 Bearer。不要沿用 QF FireSeries 路径或对百度请求做火山 HMAC。
- 取得视频任务 ID 后继续查询到终态；提交成功不等于成片。模型目录可见不等于已验证可生成。
- H5 创建成功不等于真人完成授权。未扫码查询的 `404` 必须记录真实错误，不能改写成已确认的正常 Pending。
- 控制台已有真人可查，与 API 新建 H5 是否开通是两回事；不要据一个失败否定另一个。
- 不发送未经确认的 `authorization.valid_days`，不把 H5 Token 的有效期当肖像使用期。
- `asset://asset-...` 只能引用当前提供商、账号与项目可用的素材，不自动导入账号库存给任何会员。会员隔离是使用方网关的责任，直连百度本身不会替应用隔离会员。
- 修改、删除和 H5 创建必须有当前用户授权并使用 `--allow-write`；视频创建另外必须明确获准付费并使用 `--allow-charge`。只为测试而删除已有真人素材或扫码确认不在默认授权内。
- 不打印或提交真实 Key、BytedToken、H5 链接及签名媒体 URL。若用户需要使用 H5，应在其私有应用中接收返回值，不把凭据放进公开日志或技能。
