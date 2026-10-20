# 华锐智算 Seedance API 接入说明

服务地址：`https://suanli.huaruiai.com`

提供 Seedance 视频生成、任务查询与下载，以及账号私有素材管理。视频接口支持火山方舟格式和 OpenAI Video 格式，两种格式任选一种创建即可。

## 1. 地址、API Key 与支持型号

所有请求携带华锐智算分配的 API Key：

```http
Authorization: Bearer <你的 API Key>
Content-Type: application/json
```

API Key 不等于登录密码。不要把真实 Key 放入前端代码、公开文档或共享 curl。

| 型号 | 请求中的 model |
|---|---|
| Seedance 2.0（默认） | `doubao-seedance-2-0-260128` |
| Seedance 2.0 Fast | `doubao-seedance-2-0-fast-260128` |
| Seedance 2.0 Mini | `doubao-seedance-2-0-mini-260615` |
| Seedance 2.5 | `doubao-seedance-2-5-260628` |

具体可用型号以当前 Key 的权限为准。示例默认使用 **Seedance 2.0、5 秒、720p、16:9**。其他型号的时长、分辨率及参考素材组合以该型号实际支持范围为准。

以下 curl 使用 Bash 语法，可在 Git Bash / WSL 中运行。Apipost 中配置同样的 URL、Header 和 JSON Body 即可：

```bash
export HUARUI_BASE_URL='https://suanli.huaruiai.com'
read -rsp 'API Key: ' HUARUI_API_KEY; echo
export HUARUI_API_KEY
```

查询当前 Key 可用的型号：

```bash
curl --silent --show-error --fail-with-body \
  "$HUARUI_BASE_URL/v1/models" \
  -H "Authorization: Bearer $HUARUI_API_KEY"
```

### 1.1 协议要求

服务仅接受 HTTPS。`http://suanli.huaruiai.com` 会返回 `301 Moved Permanently` 跳转到 HTTPS，多数客户端跟随 301 时把 POST 降级为 GET，导致请求落到不存在的 GET 路由：

| 客户端行为 | 响应 |
|---|---|
| Python `urllib` 跟随 301 | `404 {"error":{"message":"Invalid URL (GET /v1/videos)"}}` |
| curl 未加 `-L` | `301` + `Location: https://...`，响应体为 nginx 的 HTML |
| `POST /?Action=...` 走 HTTP | `200` 且 `Content-Type: text/html`，返回前端页面而非接口结果 |

判定方式：接口层的正常响应必为 `application/json`；`200` 加 `text/html` 说明请求未进入接口层。此类 404 与 Key、权限、余额无关，改用 HTTPS 重发即可。HTTPS 使用受信任证书，客户端保持默认校验，不要使用 `curl -k`。

## 2. 火山方舟格式：创建、查询视频

### 2.1 创建视频

`POST /api/v3/contents/generations/tasks`

```bash
curl --silent --show-error --fail-with-body \
  "$HUARUI_BASE_URL/api/v3/contents/generations/tasks" \
  -H "Authorization: Bearer $HUARUI_API_KEY" \
  -H 'Content-Type: application/json' \
  --data '{"model":"doubao-seedance-2-0-260128","content":[{"type":"text","text":"生成一个5秒的科技感城市宣传视频"}],"duration":5,"resolution":"720p","ratio":"16:9","generate_audio":true,"watermark":false}'
```

| 参数 | 类型 | 说明 |
|---|---|---|
| `model` | string，必填 | 使用第 1 节中的完整型号 ID |
| `content` | array，必填 | 文字和参考素材列表，元素格式见第 5 节 |
| `duration` | integer | 输出时长，单位秒；示例为 `5`，须符合所选型号限制 |
| `resolution` | string | 输出分辨率，示例为 `"720p"`；其他档位按所选型号支持范围使用 |
| `ratio` | string | 画面比例，示例为 `"16:9"`；其他比例按所选型号支持范围使用 |
| `generate_audio` | boolean | 是否生成声音，示例为 `true` |
| `watermark` | boolean | 是否添加水印，示例为 `false` |

布尔参数应使用 JSON 的 `true` / `false`，不要写成字符串。成功受理后返回任务 ID，例如：

```json
{"id":"task-your-created-id"}
```

这里的 ID 是占位示例。后续请求必须使用你实际收到的 `id`。受理成功不等于视频已经生成完成。

### 2.2 提示词规范与内容审核

创建接口返回 200 只代表受理成功。提示词不通过上游版权审核时，任务以 `failed` 结束：

```json
{
  "status": "failed",
  "error": {"message": "The request failed because the output video may be related to copyright restrictions. Request id: ..."},
  "usage": {}
}
```

触发条件：提示词点名具体作品、工作室、导演或"某某风格"。同一段画面描述，去掉来源名称即可通过。改写原则是把风格意图翻译为画面语言，角色与场景一律原创：

| 避免 | 改为 |
|---|---|
| 吉卜力风格 / 宫崎骏风格 | 原创手绘水彩插画风格，2D 赛璐璐上色，水彩晕染背景 |
| 某知名动画角色 | 原创角色：扎双马尾的少女，白色连衣裙 |
| 复刻某导演镜头 | 镜头从侧面缓慢横移并轻轻推近 |

提示词结构建议：风格 + 主体 + 动作 + 环境 + 光线色调 + 镜头运动 + 时长与无水印要求。示例：

```text
原创手绘水彩插画风格，治愈系夏日乡野。一个扎双马尾的原创少女站在青草山坡上，
白色连衣裙被风吹起，她伸手按住草帽；天空湛蓝飘着大朵积云，远处红色屋顶的小屋和一棵大树，
草浪随风起伏，空中飘着白色绒絮，暖色调柔和光线，水彩晕染质感，
镜头从侧面缓慢横移并轻轻推近，5 秒完整镜头，无字幕、无水印
```

审核失败同样消耗一次提交，出现该错误应先改写提示词，不要原样重试。

### 2.3 查询任务

`GET /api/v3/contents/generations/tasks/{id}`

```bash
TASK_ID='替换为创建响应中的id'
curl --silent --show-error --fail-with-body \
  "$HUARUI_BASE_URL/api/v3/contents/generations/tasks/$TASK_ID" \
  -H "Authorization: Bearer $HUARUI_API_KEY"
```

建议每 5–15 秒查询一次，并设置总超时。状态见第 4 节；成功后从 `content.video_url` 读取视频地址。

成功响应的字段示例：

```json
{
  "id": "task-your-created-id",
  "model": "doubao-seedance-2-0-260128",
  "status": "succeeded",
  "content": {"video_url": "https://media.example/result.mp4"}
}
```

示例域名和 ID 均需替换为实际返回值。视频链接可能临时有效，请及时保存。响应包含 `usage` 时，可据此查看实际用量。

从已有火山方舟客户端接入时，替换服务地址和 API Key，保留上述请求格式。最终 URL 中只保留一次 `/api/v3/contents/generations/tasks`，不要重复拼接路径。其他平台的历史任务 ID 不可直接用于查询。

## 3. OpenAI Video 格式：创建、查询与下载

### 3.1 创建视频

`POST /v1/videos`

如果已经按第 2 节创建了任务，不要重复执行本节创建请求。

```bash
curl --silent --show-error --fail-with-body \
  "$HUARUI_BASE_URL/v1/videos" \
  -H "Authorization: Bearer $HUARUI_API_KEY" \
  -H 'Content-Type: application/json' \
  --data '{"model":"doubao-seedance-2-0-260128","prompt":"生成一个5秒的科技感城市宣传视频","seconds":"5","metadata":{"resolution":"720p","ratio":"16:9","generate_audio":true,"watermark":false}}'
```

| 参数 | 类型 | 说明 |
|---|---|---|
| `model` | string，必填 | 完整型号 ID |
| `prompt` | string | 视频提示词；纯文字生成时填写 |
| `seconds` | string | 输出时长，单位秒，例如 `"5"` |
| `metadata.resolution` | string | 输出分辨率，例如 `"720p"` |
| `metadata.ratio` | string | 画面比例，例如 `"16:9"` |
| `metadata.generate_audio` | boolean | 是否生成声音 |
| `metadata.watermark` | boolean | 是否添加水印 |
| `metadata.content` | array | 参考素材列表，元素格式见第 5 节 |

保存响应中的 `id`。

> 路由说明：`POST /v1/videos` 存在，空 body 返回 `400 {"error":{"message":"Model name not specified, model name cannot be empty","type":"new_api_error"}}`。若收到 `404 Invalid URL (GET /v1/videos)`，说明请求经 HTTP 被 301 降级，见 1.1。查询路由为 `GET /v1/videos/{task_id}`，不存在的 id 返回 `400 {"code":"task_not_exist"}`。

### 3.2 查询任务

`GET /v1/videos/{id}`

```bash
TASK_ID='替换为创建响应中的id'
curl --silent --show-error --fail-with-body \
  "$HUARUI_BASE_URL/v1/videos/$TASK_ID" \
  -H "Authorization: Bearer $HUARUI_API_KEY"
```

读取顶层 `status` 和 `progress`，等待 `status` 为 `completed` 后下载。

### 3.3 下载视频

`GET /v1/videos/{id}/content`

```bash
curl --silent --show-error --fail-with-body --location \
  "$HUARUI_BASE_URL/v1/videos/$TASK_ID/content" \
  -H "Authorization: Bearer $HUARUI_API_KEY" \
  --output video.mp4
```

使用 GET 下载，勿以 HEAD 判断文件是否可下载。不要添加 `--location-trusted`，避免将 Key 转发给其他主机。

## 4. 字段与状态对照

| 含义 | 火山方舟格式 | OpenAI Video 格式 |
|---|---|---|
| 提示词 | `content` 中的 text 元素 | `prompt` |
| 时长 | `duration: 5` | `seconds: "5"` |
| 分辨率 | `resolution: "720p"` | `metadata.resolution: "720p"` |
| 参考素材 | 顶层 `content` | `metadata.content` |
| 排队 | `queued` | `queued` |
| 生成中 | `running` | `in_progress` |
| 成功 | `succeeded` | `completed` |
| 失败 | `failed` | `failed` |
| 获取成片 | `content.video_url` | `GET /v1/videos/{id}/content` |

HTTP 200 不代表生成已经成功，必须继续读取任务状态。失败时读取响应中的 `error`；不要自动重复提交生成。

### 4.1 成功响应字段

```json
{
  "id": "task_xxx",
  "model": "doubao-seedance-2-0-mini-260615",
  "status": "succeeded",
  "content": {"video_url": "https://.../xxx.mp4?X-Tos-Signature=..."},
  "duration": 5,
  "resolution": "720p",
  "ratio": "16:9",
  "framespersecond": 24,
  "generate_audio": true,
  "output_format": "mp4",
  "seed": 10559,
  "created_at": 1792476509,
  "updated_at": 1792476647,
  "upstream_id": "cgt-...",
  "execution_expires_after": 172800,
  "usage": {"completion_tokens": 108900, "total_tokens": 108900}
}
```

- `content.video_url` 为带签名的临时链接，签名有效期 24 小时（`X-Tos-Expires=86400`），须立即下载保存。
- `usage.completion_tokens` 可用于核对计费。
- `upstream_id` 为上游任务号，报障时提供。
- 5 秒 720p 任务通常在 2–3 分钟内完成，轮询间隔 10 秒即可。
- 下载后可校验产物：h264 / 1280×720 / 24fps / 时长约 5.1 秒，含 aac 音轨。

## 5. 图片、视频、音频与首尾帧

素材 URL 应是服务可访问的 HTTP(S) 地址，或通过本服务创建且属于当前账号的 `asset://` 地址。本地文件路径、`localhost` 和内网 URL 不能供远端读取。URL 有效期应覆盖排队与生成全过程。

| 用途 | type | role | URL 字段 |
|---|---|---|---|
| 图片参考 | `image_url` | `reference_image` | `image_url.url` |
| 视频参考 | `video_url` | `reference_video` | `video_url.url` |
| 音频参考 | `audio_url` | `reference_audio` | `audio_url.url` |
| 图片首帧 | `image_url` | `first_frame` | `image_url.url` |
| 图片尾帧 | `image_url` | `last_frame` | `image_url.url` |

图片参考请求体：

```json
{
  "model": "doubao-seedance-2-0-260128",
  "content": [
    {"type": "text", "text": "保持参考图中的产品一致，生成5秒科技感广告"},
    {"type": "image_url", "image_url": {"url": "https://media.example/product.png"}, "role": "reference_image"}
  ],
  "duration": 5,
  "resolution": "720p",
  "ratio": "16:9"
}
```

替换为视频或音频参考时，分别使用以下元素：

```json
{"type":"video_url","video_url":{"url":"https://media.example/reference.mp4"},"role":"reference_video"}
```

```json
{"type":"audio_url","audio_url":{"url":"https://media.example/reference.mp3"},"role":"reference_audio"}
```

OpenAI Video 格式将这些媒体元素放入 `metadata.content`，文字写在 `prompt`。不要用通用的 `reference` 作为 role；不要混用首尾帧模式和普通参考模式。默认 2.0 不以纯音频作为唯一参考，素材数量、格式和时长还需符合所选型号限制。

## 6. Seedance 素材 API

### 6.1 统一端点与公共参数

所有素材操作均使用 POST，API Key 与视频接口相同：

```http
POST /?Action=<Action>&Version=2024-01-01
Authorization: Bearer <你的 API Key>
Content-Type: application/json
X-Clover-Model: doubao-seedance-2-0-260128
```

| 参数 | 位置 | 说明 |
|---|---|---|
| `Action` | URL query，必填 | 下表中的操作名，大小写敏感 |
| `Version` | URL query，必填 | 固定为 `2024-01-01` |
| `X-Clover-Model` | Header，可选 | 默认 `doubao-seedance-2-0-260128`，须为当前 Key 有权使用的型号 |
| `ProjectName` | JSON Body，可选 | 默认 `"default"`；后续访问使用创建时相同的项目名 |

素材属于创建账号。同一账号的多个 Key 在权限允许时可访问本人素材；不同账号不能查看、修改、删除或生成引用对方素材。其他平台创建的素材 ID 不会自动成为本账号素材。

新账号的 `ListAssetGroups` / `ListAssets` 返回 `Result.TotalCount: 0` 属正常空态。验证接口连通性应使用「创建临时素材组 → 查询 → 删除」链路，该链路不产生计费，且不应用于创建素材或视频任务。

### 6.2 操作与参数

| Action | JSON Body 参数 | 说明 |
|---|---|---|
| `CreateAssetGroup` | `Name`、`GroupType`，可选 `Description` | 创建普通素材组；`GroupType` 固定为 `"AIGC"` |
| `GetAssetGroup` | `Id` | 查询本人素材组 |
| `ListAssetGroups` | 可选 `PageNumber`、`PageSize`、`Filter.GroupType` | 列出本人素材组 |
| `UpdateAssetGroup` | `Id`，以及 `Name` / `Description` | 更新本人素材组名称或描述 |
| `DeleteAssetGroup` | `Id` | 删除本人素材组，建议先删除组内素材 |
| `CreateAsset` | `GroupId`、`Name`、`AssetType`、`URL` | 在本人素材组中创建素材 |
| `GetAsset` | `Id` | 查询本人素材及处理状态 |
| `ListAssets` | 可选 `PageNumber`、`PageSize`、`Filter.GroupIds`、`Filter.GroupType` | 列出本人素材；指定 GroupIds 时只允许一个本人组 |
| `UpdateAsset` | `Id`，以及 `Name` / `Description` | 更新本人素材名称或描述，不能更换归属或素材组 |
| `DeleteAsset` | `Id` | 删除本人素材 |

所有操作均可携带 `ProjectName`。字段大小写须准确，特别是 `Id`、`GroupId`、`URL`，不要写成 `AssetId` 或 `Url`。

| 字段 | 类型与限制 |
|---|---|
| `Name` | string；创建时必填，最多 128 个字符 |
| `Description` | string；最多 2048 个字符 |
| `AssetType` | `"Image"`、`"Video"` 或 `"Audio"` |
| `URL` | 可访问的 HTTP(S) 媒体地址 |
| `PageNumber` | integer，默认 1，范围 1–10000 |
| `PageSize` | integer，默认 20，范围 1–100 |
| `Filter.GroupIds` | string[]；提供时必须恰好包含一个本人素材组 ID |

列表返回 `Result.Items`、`Result.TotalCount`、`Result.PageNumber`、`Result.PageSize`。计数仅包含本人可见素材。指定 `Filter.GroupIds` 时会刷新该组素材；未指定时返回本人已登记的素材。空数组和多个 GroupIds 均不接受。

### 6.3 创建素材组

```bash
curl --silent --show-error --fail-with-body \
  "$HUARUI_BASE_URL/?Action=CreateAssetGroup&Version=2024-01-01" \
  -H "Authorization: Bearer $HUARUI_API_KEY" \
  -H 'Content-Type: application/json' \
  --data '{"ProjectName":"default","Name":"产品素材","GroupType":"AIGC"}'
```

保存响应中的 `Result.Id`，作为后续创建素材的 `GroupId`。

### 6.4 创建素材并查询状态

把组 ID 和媒体 URL 换成真实值：

```bash
curl --silent --show-error --fail-with-body \
  "$HUARUI_BASE_URL/?Action=CreateAsset&Version=2024-01-01" \
  -H "Authorization: Bearer $HUARUI_API_KEY" \
  -H 'Content-Type: application/json' \
  --data '{"ProjectName":"default","GroupId":"group-your-created-id","Name":"产品参考图","AssetType":"Image","URL":"https://media.example/product.png"}'
```

保存响应中的 `Result.Id`，然后查询素材：

```bash
curl --silent --show-error --fail-with-body \
  "$HUARUI_BASE_URL/?Action=GetAsset&Version=2024-01-01" \
  -H "Authorization: Bearer $HUARUI_API_KEY" \
  -H 'Content-Type: application/json' \
  --data '{"ProjectName":"default","Id":"asset-your-created-id"}'
```

创建成功不等于素材已经可用。每 5–15 秒查询 `Result.Status`，仅在 `Active` 后引用；`Processing` 表示仍在处理。处理失败时按错误提示修正素材，不要无限重复创建。

### 6.5 列出本人素材

```bash
curl --silent --show-error --fail-with-body \
  "$HUARUI_BASE_URL/?Action=ListAssets&Version=2024-01-01" \
  -H "Authorization: Bearer $HUARUI_API_KEY" \
  -H 'Content-Type: application/json' \
  --data '{"ProjectName":"default","PageNumber":1,"PageSize":20,"Filter":{"GroupIds":["group-your-created-id"],"GroupType":"AIGC"}}'
```

### 6.6 使用本人素材生成视频

将 URL 写为 `asset://` 加素材的完整 ID，不能使用组 ID：

```bash
curl --silent --show-error --fail-with-body \
  "$HUARUI_BASE_URL/api/v3/contents/generations/tasks" \
  -H "Authorization: Bearer $HUARUI_API_KEY" \
  -H 'Content-Type: application/json' \
  --data '{"model":"doubao-seedance-2-0-260128","content":[{"type":"text","text":"保持产品外观一致，生成5秒科技感广告"},{"type":"image_url","image_url":{"url":"asset://asset-your-created-id"},"role":"reference_image"}],"duration":5,"resolution":"720p","ratio":"16:9"}'
```

素材必须属于当前账号、处于 `Active` 状态且适用于所选型号。其他账号、其他平台或不同资源范围的素材不可直接混用。此请求会创建视频任务，可能计费。

### 6.7 真人授权（需确认开通）

普通素材入库不能代替真人授权。真人授权接口的开通范围请向服务方确认后使用：

| Action | JSON Body 参数 | 返回内容 |
|---|---|---|
| `CreateVisualValidateSession` | 可选 `CallbackURL`、`ProjectName` | `Result.BytedToken`、`Result.H5Link` |
| `GetVisualValidateResult` | `BytedToken`、可选 `ProjectName` | 授权结果；成功时包含 `GroupId` |

`CallbackURL` 可省略，服务端根据已配置的公网域名生成通知地址；客户需要自行接收通知时，可填写自己控制的绝对 HTTPS 地址。`ProjectName` 默认为 `default`，查询时保持与创建一致。

创建授权链接：

```bash
curl --silent --show-error --fail-with-body \
  "$HUARUI_BASE_URL/?Action=CreateVisualValidateSession&Version=2024-01-01" \
  -H "Authorization: Bearer $HUARUI_API_KEY" \
  -H 'Content-Type: application/json' \
  --data '{"ProjectName":"default"}'
```

需要自行接收通知时，将 Body 改为：

```json
{"ProjectName":"default","CallbackURL":"https://your-service.example/seedance/authorization/callback"}
```

保存响应中的 `Result.BytedToken`，将 `Result.H5Link` 交给授权人本人完成操作。会话创建成功、授权页面能打开都不表示认证或同意已经完成；未完成会话最长有效 24 小时，过期后重新创建。

授权人完成操作后查询结果：

```bash
curl --silent --show-error --fail-with-body \
  "$HUARUI_BASE_URL/?Action=GetVisualValidateResult&Version=2024-01-01" \
  -H "Authorization: Bearer $HUARUI_API_KEY" \
  -H 'Content-Type: application/json' \
  --data '{"ProjectName":"default","BytedToken":"替换为本账号创建会话返回的Token"}'
```

查询必须使用同一账号的 API Key 和真实 `BytedToken`。成功结果需包含 `ResultCode=10000` 及 `GroupId`，不能通过自行填写组 ID 获得授权。使用返回的 `GroupId` 按第 6.5 节查询本人组内素材；真人组筛选使用 `Filter.GroupType="LivenessFace"`，不要继续使用普通组的 `AIGC`。待素材 `Active` 后，使用素材 ID 而不是组 ID 拼接 `asset://` 引用。

自动核对功能启用后，服务端收到通知会核实授权结果，并约每分钟补查未完成且未过期的会话；客户无需配置定时任务或保持网页打开。客户指定自己的 `CallbackURL` 不影响服务端补查，也不影响主动查询。未完成、上游查询失败和伪造通知都不能视为授权成功。

默认通知接收路径为 `POST /api/seedance/authorization/callback`，由服务端接收，客户无需主动调用。客户自设回调时，收到通知后仍应用自己的 API Key 查询结果，不能直接相信通知中的素材组或身份字段。

真人授权与自动核对的开通状态请向服务方确认。旧授权链接若不支持自动核对，请重新创建；不要因为查询失败就无限重复创建。上游 `404 token not found` 不应直接解释成正常等待或授权成功，应保留脱敏错误并联系服务方排查。

`BytedToken` 和 H5 链接属于敏感会话数据，不放入日志或共享示例。只有通过本人会话核验成功的素材组才可使用；自行填写 GroupId 或收到通知不能代替结果核验。

## 7. 错误处理与注意事项

| 现象 | 处理建议 |
|---|---|
| 400 | 检查 JSON、参数大小写、媒体 role、时长和分辨率 |
| 401 | 检查 API Key 是否有效，是否正确携带 `Bearer ` 前缀 |
| 403 | 检查 Key 权限、可用型号、账户余额和 Key 限额 |
| 404 | 检查 ID 是否来自本人创建结果；他人、未绑定或过期资源不可访问 |
| `404 Invalid URL (GET /v1/videos)` 等 | 请求使用 `http://` 被 301 降级（POST 变 GET），改用 `https://` 重发 |
| 429 | 降低频率；素材接口每账号每分钟最多 120 次，多 Key 共用 |
| 视频任务 `failed`，`error.message` 含 copyright restrictions | 提示词点名了作品/工作室/导演/风格来源，改为画面语言描述后重发，见 2.2 |
| 视频任务 `failed`，其他原因 | 读取任务 `error` 和 `upstream_id`，修正问题后再决定是否重新生成 |
| `200` 但返回 `text/html` | 请求未进入接口层，检查协议与路径；接口层响应必为 JSON 或下载文件 |

素材错误可从 `ResponseMetadata.Error.Code` / `Message` 读取；视频请求错误按实际响应的 `error` 或 `code` / `message` 读取。

- 创建任务可能预扣额度，完成后按实际用量结算；余额与 Key 限额都应足够。具体价格按服务约定执行。
- 创建超时或响应丢失时，先确认是否已受理，不要自动重复 POST。两种格式不要为同一视频各创建一次。
- 查询和下载使用返回的真实任务 ID；素材操作使用真实素材/组 ID，示例中的占位值不可直接调用。
- 媒体 URL 应在整个处理期间保持可访问，生成结果请及时下载保存。
- 真人、肖像和参考素材须具有合法使用权限。上传成功、素材 Active 和真人授权成功是不同状态。
- 排障时提供请求时间、型号、HTTP 状态、Request ID 和脱敏错误；不要提供真实 Key、授权 token 或带签名的媒体链接。
