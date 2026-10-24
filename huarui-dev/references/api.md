# 华锐通用 API 参考

本文件面向华锐自用开发，只记录通用协议，不包含客户 Key、客户素材 ID、固定账号库存、内部回调路径或内部自动核对业务逻辑。真实请求只能使用环境变量 `HUARUI_BASE_URL` / `HUARUI_API_KEY`，且必须获得本次操作授权。

## 1. 鉴权、模型与安全传输

请求头：

```http
Authorization: Bearer <HUARUI_API_KEY>
Content-Type: application/json
```

候选模型以当前账号通过 `GET /v1/models` 实际可见结果为准，例如 `doubao-seedance-2-0-260128`、`doubao-seedance-2-0-fast-260128`、`doubao-seedance-2-0-mini-260615`、`doubao-seedance-2-5-260628`。可见不代表所有收费能力或扩展参数均已开通。

服务要求 HTTPS。若 HTTP 重定向导致 POST 变 GET，可能出现 `404 Invalid URL (GET ...)`；若接口返回 HTML，先检查协议、域名和路径。保持证书校验，不使用 `curl -k`，不跨主机转发 Authorization。

## 2. Ark 兼容视频协议

- 创建：`POST /api/v3/contents/generations/tasks`
- 查询：`GET /api/v3/contents/generations/tasks/{id}`
- 提示词与参考素材：顶层 `content`
- 时长：整数 `duration`
- 分辨率、比例、声音、水印：顶层 `resolution`、`ratio`、`generate_audio`、`watermark`

通用请求形状：

```json
{
  "model": "doubao-seedance-2-0-mini-260615",
  "content": [{"type": "text", "text": "<原创提示词>"}],
  "duration": 5,
  "resolution": "720p",
  "ratio": "16:9",
  "generate_audio": true,
  "watermark": false
}
```

成功受理返回真实任务 `id`，不等于生成成功。查询状态通常为 `queued`、`running`、`succeeded`、`failed`；成功成片通常在 `content.video_url`，须及时私下下载。

## 3. OpenAI Video 协议

- 创建：`POST /v1/videos`
- 查询：`GET /v1/videos/{id}`
- 下载：`GET /v1/videos/{id}/content`
- 提示词：`prompt`
- 时长：字符串 `seconds`
- 参考素材及输出选项：`metadata`

通用请求形状：

```json
{
  "model": "doubao-seedance-2-0-mini-260615",
  "prompt": "<原创提示词>",
  "seconds": "5",
  "metadata": {
    "resolution": "720p",
    "ratio": "16:9",
    "generate_audio": true,
    "watermark": false
  }
}
```

状态通常为 `queued`、`in_progress`、`completed`、`failed`。同一视频只选一种创建协议，不要重复提交；创建超时先按原协议查询。

## 4. 素材与 Action

素材 Action 统一使用：`POST /?Action=<Action>&Version=2024-01-01`，沿用华锐 Bearer。可选 `X-Clover-Model` 指定当前 Key 有权使用的型号；`ProjectName` 默认 `default`，后续访问保持一致。

常见 Action：

| Action | 通用字段 |
|---|---|
| `CreateAssetGroup` | `Name`、`GroupType: AIGC`，可选 `Description` |
| `GetAssetGroup` / `DeleteAssetGroup` | `Id` |
| `ListAssetGroups` | `PageNumber`、`PageSize`、可选 `Filter.GroupType` |
| `UpdateAssetGroup` | `Id`、`Name`/`Description` |
| `CreateAsset` | `GroupId`、`Name`、`AssetType: Image/Video/Audio`、`URL` |
| `GetAsset` / `DeleteAsset` | `Id` |
| `UpdateAsset` | `Id`、`Name`/`Description` |
| `ListAssets` | 分页字段，可选 `Filter.GroupType`、本人单一 `Filter.GroupIds` |

创建素材后查询状态，只有 `Active` 才可引用；`Processing` 不是完成。视频参考的通用内容元素如下：

```json
{"type":"image_url","image_url":{"url":"asset://<本人素材ID>"},"role":"reference_image"}
{"type":"video_url","video_url":{"url":"https://media.example/reference.mp4"},"role":"reference_video"}
{"type":"audio_url","audio_url":{"url":"https://media.example/reference.mp3"},"role":"reference_audio"}
```

Ark 兼容格式把元素放入顶层 `content`；OpenAI Video 格式把素材数组放入 `metadata.content`。首帧与尾帧分别使用 `first_frame` / `last_frame`，不要与普通参考模式混用；不要使用泛化的 `reference` role。素材必须是当前账号合法可用的 `asset://<素材ID>` 或上游可访问的 HTTPS 地址，不使用组 ID、本地路径、内网地址或其他账号库存。

## 5. 真人授权边界

真人授权能力需服务方明确开通。普通素材入库不能替代本人授权；授权必须由本人完成，不能由代理代替同意。会话链接、Token、签名 URL 和私人照片不得写入日志、Git 或共享示例。不要在开发包中固化真人素材、会话结果、回调路径或自动核对流程；若业务需要，应接入拥有明确授权的独立事实源。

## 6. 状态、错误与验收

- `400`：检查 JSON、字段大小写、role、模型及时长/分辨率限制。
- `401`：检查环境变量和 `Bearer` 前缀。
- `403`：检查型号权限、余额和限额。
- `404`：检查协议、真实任务/素材 ID、账号归属及有效期；不要猜测其他账号资源。
- `429`：降低频率，遵守服务方当前限流。
- `failed`：读取真实 `error`；版权审核失败时改用原创主体和画面语言，不原样重复提交。
- `200` + `text/html`：检查 HTTPS、域名和路径。

HTTP 200 只代表请求受理或查询成功，不代表视频已生成。验收应记录脱敏的 provider、型号、HTTP、RequestId、任务终态和本地产物检查结果；不记录 Key、Token、素材库存或带签名链接。不得自动轮询或执行真实接口，除非本次用户授权明确覆盖。
