# 华锐 Seedance：非敏感协议差异

本文件仅整合 `huarui-zhisuan/SKILL.md` 与 `huarui-zhisuan/references/seedance-api.md` 的公开协议差异，属于 `seedance-dev` 的 `provider=huarui` 开发参考；不包含客户包原文、客户硬编码 Key、固定账号或素材库存。本次未请求服务，服务方能力与开通状态须按当前账号确认。

## 1. 地址、凭据与传输

```dotenv
HUARUI_BASE_URL=https://suanli.huaruiai.com
HUARUI_API_KEY=<客户提供Key，仅在环境或本机私有配置中设置>
```

视频和素材都用 `Authorization: Bearer $HUARUI_API_KEY`、JSON `Content-Type: application/json`。不使用官方素材 AK/SK 签名，不把华锐 Key 发给官方或百度。本技能 Ark CLI 不支持此 provider，不能通过修改它的端点接入。

始终直接使用 HTTPS，保持证书校验；HTTP 301 可能让客户端将 POST 降级为 GET，产生 `Invalid URL (GET ...)` 或前端 HTML。JSON API 返回 HTML 时先检查域名、协议和路径，不直接判断 Key/余额问题。下载路由可返回文件。禁止跨主机转发 Authorization。

候选模型为 `doubao-seedance-2-0-260128`、`doubao-seedance-2-0-fast-260128`、`doubao-seedance-2-0-mini-260615`、`doubao-seedance-2-5-260628`；通过获准的 `GET /v1/models` 确认可见型号。列表可见不证明收费生成或所有扩展参数均已验收。

## 2. 两种视频格式：只选一种创建

| 含义 | Ark 兼容格式 | OpenAI Video 格式 |
|---|---|---|
| 创建 | `POST /api/v3/contents/generations/tasks` | `POST /v1/videos` |
| 查询 | `GET /api/v3/contents/generations/tasks/{id}` | `GET /v1/videos/{id}` |
| 提示词 | 顶层 `content` 中 text | `prompt` |
| 时长 | `duration: 5`，整数 | `seconds: "5"`，字符串 |
| 参考素材 | 顶层 `content` | `metadata.content` |
| 分辨率/比例/声音/水印 | 顶层 `resolution/ratio/generate_audio/watermark` | `metadata` 中同名字段 |
| 排队/运行/成功/失败 | `queued/running/succeeded/failed` | `queued/in_progress/completed/failed` |
| 成片 | `content.video_url` | `GET /v1/videos/{id}/content` |

最小请求体模板（示例不表示允许收费调用）：

```json
{"model":"doubao-seedance-2-0-mini-260615","content":[{"type":"text","text":"<原创提示词>"}],"duration":5,"resolution":"720p","ratio":"16:9","generate_audio":true,"watermark":false}
```

对应 OpenAI 包装：

```json
{"model":"doubao-seedance-2-0-mini-260615","prompt":"<原创提示词>","seconds":"5","metadata":{"resolution":"720p","ratio":"16:9","generate_audio":true,"watermark":false}}
```

保存真实返回的任务 ID；创建 200 只代表受理。按创建格式查询，每 5–15 秒并设置总超时，成功后 GET 下载；不使用 HEAD 判断可下载，不将其他渠道的任务 ID 混入。临时签名 URL 及时转存（源资料描述通常 24 小时，以实际响应为准），不在日志暴露。

保留实际 `duration/resolution/ratio/framespersecond`、`usage.completion_tokens`、`upstream_id` 等安全验收信息，不保证固定耗时或成片规格。创建超时先确认受理状态，不自动重复 POST。

## 3. 媒体与素材 Action

| 目的 | type | role |
|---|---|---|
| 图片参考 | `image_url` | `reference_image` |
| 视频参考 | `video_url` | `reference_video` |
| 音频参考 | `audio_url` | `reference_audio` |
| 首帧/尾帧 | `image_url` | `first_frame/last_frame` |

媒体 URL 放入对应 `image_url.url/video_url.url/audio_url.url`。使用可被上游访问的媒体地址或本账号合法的 `asset://<素材ID>`，不使用组 ID、本地路径、内网 URL 或其他账号库存。不得用通用 `reference` role；首尾帧与普通参考模式不混用；默认 2.0 不以音频作为唯一参考。

素材统一 `POST /?Action=<Action>&Version=2024-01-01`，同一华锐 Bearer；可选 `X-Clover-Model` 指定有权使用的型号，源协议默认 2.0 标准版。`ProjectName` 默认 `default`，后续保持一致。

| Action | 核心 JSON 字段 |
|---|---|
| `CreateAssetGroup` | `Name`、`GroupType: AIGC`，可选 `Description` |
| `GetAssetGroup/DeleteAssetGroup` | `Id` |
| `ListAssetGroups` | `PageNumber/PageSize`，可选 `Filter.GroupType` |
| `UpdateAssetGroup` | `Id`、`Name/Description` |
| `CreateAsset` | `GroupId`、`Name`、`AssetType: Image/Video/Audio`、`URL` |
| `GetAsset/DeleteAsset` | `Id`，不是 `AssetId` |
| `UpdateAsset` | `Id`、`Name/Description`，不能改变归属 |
| `ListAssets` | 分页、`Filter.GroupType`、可选 `Filter.GroupIds` |

源协议的 `Filter.GroupIds` 提供时恰好一个本人组，不能传空或多个；列表计数仅含本人可见内容，不代替会员侧归属管理。分页 `PageNumber` 1–10000、`PageSize` 1–100；名称最多 128 字符，描述最多 2048，按服务方当前 schema 核对。响应通常为 `ResponseMetadata` + `Result`，列表包含 Items/TotalCount 等。

素材创建后查询到 `Active` 才引用，`Processing` 不是完成。普通 AIGC 组不能替代真人认证。创建/改名/删除组即使源资料称无计费，也是外部写操作，默认不做连通性测试；必须获准并限定本次创建的资源。删除素材/组不等于撤回肖像授权。

## 4. 真人授权：不可套用官方契约

需向服务方确认 H5 与自动核对功能开通；普通上传不能代替本人授权。

| Action | 请求 | 源协议结果 |
|---|---|---|
| `CreateVisualValidateSession` | 可选 `CallbackURL`、`ProjectName` | `Result.BytedToken`、`Result.H5Link` |
| `GetVisualValidateResult` | 同账号 `BytedToken`，同项目 | 核验成功需 `ResultCode=10000` 及 `GroupId` |

华锐允许省略 `CallbackURL`，由服务端配置公网通知地址；自定义时用受控绝对 HTTPS 地址。源协议的默认通知路径为服务端 `POST /api/seedance/authorization/callback`，启用自动核对后会查询结果并补查未完成会话。这是华锐网关行为，不是官方 H5 浏览器 GET 回跳的同义替代，也不能承诺百度提供相同行为。

通知不可信任为授权证据：仍使用同账号私有 Key/Token 主动查询核验；未完成、上游失败、伪造通知都不是授权成功。成功后按返回组查询 `Filter.GroupType: LivenessFace` 的本人素材，等待 `Active`，再使用素材 ID。

源协议描述未完成会话最长有效 24 小时；这是华锐会话语义，不等于肖像授权期限，也不能覆盖官方 30 分钟 Token。不能承诺自定义肖像有效期或主动撤权 API。真实 404 token not found 保留脱敏失败，不改写成正常 Pending，不无限创建。Token/H5Link 不进日志/Git，不让代理代替真人完成同意。

## 5. 错误、费用与授权

- 400：核对格式、大小写、role 和模型参数；401：核对 Bearer；403：核对型号权限、余额与限额；429：降低频率。源协议素材限制为每账号每分钟最多 120 次，多 Key 共用，当前服务限制优先。
- 404：除 HTTP 降级问题外，核对 ID 的渠道、本人归属及有效期；不猜测其他账号资源。
- 版权审核失败等 `failed`：保留错误和 upstream_id，改用原创主体和具体画面语言，不原样重复提交；不把改写描述当成保证通过审核的方法。
- 创建任务可能预扣额度并按实际用量结算，真人会话也可能计费或占额度；不推断失败免费，不固定报价。所有创建/更新/删除/收费生成均在当前用户授权范围内执行。
- 排障仅记录请求时间、provider、型号、HTTP、RequestId、任务终态和脱敏摘要，不输出 Key、库存、授权 Token、私人照片或签名 URL。
