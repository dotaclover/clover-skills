---
name: seedance-dev
description: 用于自用 Seedance 开发、接口整合及生成工作流，显式选择 provider=ark/baidu/huarui，区分官方、百度 AI 网关与华锐的视频、素材、真人授权协议，完成格式确认、提交、轮询、下载与验收；不替代独立客户交付包。
agent_created: true
---

# Seedance 自用开发与接口整合

统一工作流，不统一供应商凭据、库存、权益或成功证据。先显式选择 `provider=ark`、`provider=baidu` 或 `provider=huarui`；缺省不猜测、不切换供应商，不从客户交付包读取配置。

## 三方接入边界

| provider | Base URL | 认证 | 视频请求格式 |
|---|---|---|---|
| `ark` | 视频 `https://ark.cn-beijing.volces.com/api/v3`；素材 `https://ark.cn-beijing.volcengineapi.com/` | 视频 `ARK_API_KEY` Bearer；素材 `ARK_ASSET_ACCESS_KEY` + `ARK_ASSET_SECRET_KEY` HMAC V4 | `/contents/generations/tasks`，顶层 `content`、整数 `duration` |
| `baidu` | `https://ai-gateway.baidubce.com` | 视频、素材均 `BAIDU_AI_KEY` Bearer | `/api/v3/contents/generations/tasks`，顶层 `content`、整数 `duration`；不是 QF FireSeries |
| `huarui` | `https://suanli.huaruiai.com` | 视频、素材均 `HUARUI_API_KEY` Bearer，由客户提供并放入环境变量 | Ark 兼容 `/api/v3/contents/generations/tasks`；或 `/v1/videos` 使用 `prompt`、字符串 `seconds`、`metadata`，二选一 |

- 素材 Action 均涉及 `/?Action=<Action>&Version=2024-01-01`，但 Ark 必须使用独立素材域名及 HMAC，百度/华锐使用各自网关和 Bearer。字段大小写敏感，不能只替换域名复用认证。
- Ark 项目由 `ARK_ASSET_PROJECT_NAME` 指定，未设置为 `default`；各渠道项目映射与账号库存不互通，不能把账号库存自动分配给全部会员。
- 普通素材入库、状态 `Active`、真人同意及生成可用是四个不同检查项。`asset://<素材ID>` 只引用当前用户、当前渠道合法授权且适用的素材；组 ID 不能代替素材 ID。
- Ark H5 的 `CallbackURL` 必填，短期 Token 与肖像授权期限不同；当前历史账号新建 H5 受订阅限制。百度 H5 的结果与限制只从百度事实源核对，不把创建成功当真人闭环。华锐允许省略回调，有服务端通知/补查差异，必须按华锐协议核验，不能套用官方字段或期限。
- 创建视频可能收费；素材/H5 写操作可能占额度，删除不可逆。分别确认用户允许的渠道、资源、费用和外部写范围；不能因资料称“免费”便自动创建/删除测试组。查询不是收费生成授权，CLI 开关也不是用户授权。
- 不保存硬编码 Key、固定客户账号库存、真实素材 ID、BytedToken、H5 链接或签名 URL。客户交付包保持独立，不复制、不移动、不改名。

## 统一任务流程

1. **选择 provider**：确认业务账号、项目、凭据变量和请求域名。先读对应参考；将证据标注为“历史记录”“当前账号实测”或“未验证”，不能跨渠道移用。
2. **确认模型与格式**：确定文生视频、首帧/首尾帧、多模态参考或编辑/延长，核对该渠道该型号的时长、分辨率、比例、声音和输出格式。首尾帧与普通参考模式不可混用；尾帧搭配首帧。2.0 不以纯音频作为唯一参考。2.5 扩展参数不从旧文档直接推断可用。检查媒体可访问性与权利，真人必须完成本人授权核验。
3. **提交**：明确费用/写入授权后只提交一次，保存 provider、格式、model、任务 ID、HTTP 和 RequestId。默认最小无参考测试也须先获准。响应丢失/超时先排查受理状态，不自动重试 POST，不为同一视频用两种格式各创建一次。
4. **轮询**：使用同一 provider、账号及创建格式查询，设置间隔（官方通常 10–30 秒；华锐按参考 5–15 秒）、总超时和速率限制。Ark 格式 `queued/running` 非成功；只有 `succeeded` 且存在成片才进入下载。华锐 OpenAI 格式使用 `in_progress/completed`。失败/过期/取消保留真实错误，不将 404 改写成 Pending，不自动重提生成。
5. **下载与验收**：从 Ark 格式的 `content.video_url` 或华锐 `/v1/videos/{id}/content` 下载到本地，临时链接及时私下转存，不作永久地址；下载时不要将 API Key 转发给媒体域名。核对文件非空、可播放、实际时长、尺寸、编码、帧率、声音、内容和用量；任务成功与成片验收分别报告。可用本地媒体检查工具并用 `present_files` 展示本地产物，不能仅返回任务 ID 或临时 URL。

## 资料路由与唯一事实源

- 官方完整参考与融合后的生成流程：[ark-api.md](references/ark-api.md)。官方历史实测：[ark-verification.md](references/ark-verification.md)，保留订阅限制、已授权查询和未验证事项。
- 百度差异索引：[baidu-seedance.md](references/baidu-seedance.md)。**`baidu-api-dev` 是唯一百度接口事实源**；实际协议、实测、CLI 读取该目录，不在本技能复制全部百度资料。独立分发本 zip 不包含该依赖，缺少它时先取得对应资料，不按索引猜测执行。
- 华锐开发唯一事实源：[../huarui-dev](../huarui-dev)，仅使用 `HUARUI_BASE_URL` / `HUARUI_API_KEY` 环境变量；不携带客户配置。`huarui-video` 仅供华锐内部官方真人视频，不是通用入口；`huarui-zhisuan` 是客户交付包，不从中读取配置。
- 历史入口原文：[legacy-seedance-ark.md](references/legacy-seedance-ark.md)、[legacy-seedance-video.md](references/legacy-seedance-video.md)。仅用于追溯，不是独立激活入口，不用旧的固定价格/上限/真人限制覆盖当前证据。

## Ark CLI：只支持官方

`scripts/seedance.py` 仅固定连接官方 Ark，保留原有认证、默认脱敏和写入/计费门禁；不自动选择百度或华锐，不读取客户包凭据。只从当前环境或显式 `--env-file` 载入本机私有配置，不扫描其他目录。

```bash
python scripts/seedance.py --help
```

- `video-get`、`video-list`：官方视频只读查询；`video-create --allow-charge`：最小文生视频，不支持任意多模态 JSON、自动轮询或下载。
- `asset-action`：官方 HMAC Action；非只读 Action 必须 `--allow-write`。所有真实调用另需当前任务授权。
- `--private-output` 会写入原始敏感响应，仅允许新的本机私有文件；不加入 Git、不写共享日志。模型和请求能力以参考为准，不以该最小 CLI 的参数范围代替全 API。
- 百度 CLI 保留在 `../baidu-api-dev/scripts/seedance.py`；华锐按参考自行集成，不借用本脚本绕过 provider 隔离。
