# Seedance 素材库

聚合 API 的素材管理接口用于导入公网图片、视频或音频，查询异步处理状态，把素材用于 Seedance 视频生成，并通过独立会话完成真人模特授权。先按 [SKILL.md](../SKILL.md) 完成鉴权和环境变量设置。

## 接口清单

所有命令从技能目录运行，使用已保存的凭据；如需切换可信服务根地址，在 `material` 后传 `--base-url`。

| 操作 | 命令 |
| --- | --- |
| 创建分组 | `python scripts/juhe.py material groups create --name <名称> --description <描述> --model <Seedance型号>` |
| 分组列表 | `python scripts/juhe.py material groups list --group-type AIGC` |
| 查询分组 | `python scripts/juhe.py material groups get --id <分组ID>` |
| 修改分组 | `python scripts/juhe.py material groups update --id <分组ID> --name <名称>` |
| 删除分组 | `python scripts/juhe.py material groups delete --id <分组ID>` |
| 创建素材 | `python scripts/juhe.py material assets create --group-id <分组ID> --url <公网URL> --name <名称> --asset-type Image` |
| 素材列表 | `python scripts/juhe.py material assets list --group-id <分组ID> --status Active` |
| 查询素材 | `python scripts/juhe.py material assets get --id <素材ID>` |
| 修改素材名称 | `python scripts/juhe.py material assets update --id <素材ID> --name <名称>` |
| 删除素材 | `python scripts/juhe.py material assets delete --id <素材ID>` |
| 创建真人认证会话 | `python scripts/juhe.py material liveness create --name <名称> --model <Seedance型号>` |
| 查询真人认证结果 | `python scripts/juhe.py material liveness get --id <认证组ID>` |

CLI 原样输出服务返回的 JSON；成功响应保留 `code`、`message`、`request_id`、`result`。`code: 0` 只表示接口调用成功，素材仍需等待异步处理并通过审核。

- 分组 ID 和素材 ID 均以接口返回值为准，后续命令原样传入。
- 素材通过公网 URL 导入，不接收本地文件或 multipart 上传。
- 创建普通素材必须传入自己的 `GroupId`；普通分组只支持 `GroupType: AIGC`。
- 分组列表必须带 `--group-type`，普通分组使用 `AIGC`；素材列表不支持 `GroupType`，只能按 `--group-id`、`--status` 过滤。
- 删除素材用查询串 `?id=<素材ID>`，删除分组用请求体 `{"Id": "<分组ID>"}`；CLI 已封装正确用法。
- `--model` 用于选择素材所属服务账户；不传时沿用分组记录的型号。模型必须对当前 Key 可见并有权限。

## 创建与查询

```bash
python scripts/juhe.py material groups create   --name '角色素材'   --description '视频参考素材'   --model 'doubao-seedance-2-0'

python scripts/juhe.py material assets create   --group-id '<创建分组返回的 result.id>'   --url 'https://example.com/reference.jpg'   --name '角色正面'   --asset-type Image

python scripts/juhe.py material assets get --id '<创建素材返回的 result.id>'
```

`AssetType` 为 `Image`、`Video` 或 `Audio`。查询响应中的 `result.Status`：

| 状态 | 操作 |
| --- | --- |
| `Processing` | 等待后重新查询，建议间隔 3–5 秒 |
| `Active` | 可以使用 |
| `Failed` | 读取 `result.Error.Code` / `result.Error.Message`，修正或重建素材 |

查询结果中的 `result.URL` 按接口说明有效期为 12 小时。视频生成前重新查询素材，不要长期缓存 URL。

## 在 Seedance 中引用素材

### 直接使用查询结果 URL

2026-10-22 的真实付费测试已验证：`doubao-seedance-2-0-mini-260615` 可直接读取素材查询返回的 `result.URL`，无需再次转存。参考图片和参考视频任务均成功完成。

先等待 `Status: Active`，再把 `result.URL` 放入对应媒体字段：

```json
{"type":"image_url","image_url":{"url":"<result.URL>"},"role":"reference_image"}
```

```json
{"type":"video_url","video_url":{"url":"<result.URL>"},"role":"reference_video"}
```

聚合 API 会把该 URL 原样转发给视频服务，不会替调用方重新查询素材或检查 `Active`。调用方必须在提交前自行确认状态。本次测试中返回 URL 与最初导入的公网源 URL 相同，不一定是签名 URL；不能据此假设任意源 URL 都会保持可读，也不能假设查询结果永远不变。

### 使用 asset:// 素材 ID

聚合 API 还提供 `asset://` 素材引用扩展。把素材查询结果中的 `ID` 原样接在 `asset://` 后；提交时平台会校验素材归属、类型、`Active` 状态和所属分组，并把公共 ID 改写成服务可识别的原生素材 URI。

**`asset://` 是聚合 API 扩展，不是公开的媒体 URL，也不是素材查询响应中的 URL 格式。** 网关完成校验后改写的原生 URI 只在请求内部使用，调用方不需要也不能自行构造。

内容接口格式在 `/api/v3/contents/generations/tasks` 的顶层 `content` 中使用：

```json
{
  "model": "doubao-seedance-2-0-mini-260615",
  "content": [
    {"type": "text", "text": "保持参考图中的主体外观，镜头缓慢推进，5秒，无字幕。"},
    {"type": "image_url", "image_url": {"url": "asset://<素材ID>"}, "role": "reference_image"}
  ],
  "duration": 5,
  "resolution": "720p",
  "ratio": "16:9"
}
```

`/v1/video/generations` 和 `/v1/videos` 使用 `metadata.content`：

```json
{
  "model": "doubao-seedance-2-0-mini-260615",
  "prompt": "保持参考图中的主体外观，镜头缓慢推进，5秒，无字幕。",
  "seconds": "5",
  "metadata": {
    "content": [
      {"type": "text", "text": "保持参考图中的主体外观，镜头缓慢推进，5秒，无字幕。"},
      {"type": "image_url", "image_url": {"url": "asset://<素材ID>"}, "role": "reference_image"}
    ],
    "resolution": "720p",
    "ratio": "16:9"
  }
}
```

视频和音频素材分别使用 `video_url.url` / `reference_video`、`audio_url.url` / `reference_audio`。图片也可按模型要求使用 `first_frame` 或 `last_frame`。

同一条视频请求的素材应创建在同一分组，并属于同一服务账户。混用不同账户会返回 `material_account_mismatch`。

## 真人模特与 LivenessFace

真人模特不是 `reference_image` 的一种角色，也不是普通 AIGC 素材。它需要真人本人通过独立 H5 会话完成身份核验与肖像授权，授权结果绑定到 `LivenessFace` 素材组；普通 URL 导入、AIGC 分组和 `asset://` 引用都不能替代该同意流程。

### 创建认证会话

```bash
python scripts/juhe.py material liveness create   --name '真人模特授权'   --description '本人完成活体认证'   --model 'doubao-seedance-2-0'
```

成功响应返回：

- `result.GroupId`：聚合 API 的认证组 ID，后续查询和上传真人素材都使用它。
- `result.H5Link`：一次性交给真人本人在手机端完成认证的授权链接。

只需要保存或转发 `result.GroupId`。`result.H5Link` 属敏感链接，不应落库、写入日志、保存到技能目录，也不要粘贴到公开位置。

### 查询认证结果

```bash
python scripts/juhe.py material liveness get --id '<result.GroupId>'
```

| `result.Status` | 操作 |
| --- | --- |
| `running` | 真人尚未完成认证；等待后继续查询 |
| `completed` | 认证完成，可向该认证组上传真人素材 |

认证必须由真实自然人本人完成，程序侧不能代办、伪造或复用他人的认证结果。认证完成前向该组创建素材会返回 `material_group_not_verified`。

认证完成后，使用认证组 ID 创建素材：

```bash
python scripts/juhe.py material assets create   --group-id '<result.GroupId>'   --url 'https://example.com/portrait.jpg'   --asset-type Image
```

认证组在列表中显示为 `LivenessFace`。普通 `AIGC` 分组不能改成真人认证组；需要真人模特时应从 `material liveness create` 开始。不得把普通素材查询成功当作真人授权成功。

## 创建、列表、改名与删除

分组 `Name` 最长 64 字符，`Description` 最长 300 字符。素材 `Name` 可选，最长 64 字符。

```bash
# 普通分组列表
python scripts/juhe.py material groups list   --group-type AIGC --page-number 1 --page-size 20

# 素材列表，可按分组和 Active 状态过滤
python scripts/juhe.py material assets list   --group-id '<分组ID>' --status Active   --page-number 1 --page-size 20

# 修改素材名称
python scripts/juhe.py material assets update   --id '<素材ID>' --name '角色正面新版名称'

# 删除素材
python scripts/juhe.py material assets delete --id '<素材ID>'
```

列表必填 `PageNumber`（从 1 开始）和 `PageSize`（1–100）。分组列表必须传 `Filter.GroupType`，普通分组通常为 `AIGC`；素材列表不接受 `Filter.GroupType`，传了会返回 `invalid_parameter`。素材列表可传 `Filter.GroupIds`（`--group-id`）和 `Filter.Statuses`（`--status`）。先删除组内全部素材，再删除分组。

删除素材把素材 ID 放在查询串 `?id=<素材ID>`；删除分组把分组 ID 放在 JSON 请求体 `{"Id": "<分组ID>"}`。两种形式不同，CLI 已封装正确用法，不要互相替换。

## 素材规格

| 类型 | 主要限制 |
| --- | --- |
| 图片 | jpeg/png/webp/bmp/tiff/gif/heic/heif；宽高比 > 0.4 且 < 2.5；边长 > 300 且 < 6000 px；< 30 MB |
| 视频 | mp4/mov；2–15 秒；宽高比 0.4–2.5；边长 300–6000 px；总像素 409600–2086876；<= 50 MB；24–60 FPS |
| 音频 | wav/mp3；2–15 秒；<= 15 MB |

最终以素材处理结果为准。

## 常见错误

| 错误 | 处理 |
| --- | --- |
| `material_not_active` | 重新查询；`Processing` 时等待，`Failed` 时查看 `Error` 并修正 |
| `material_account_mismatch` | 同一请求的素材必须来自同一服务账户，建议建在同一分组 |
| `material_type_mismatch` | `Image` 只能放图片字段，`Video` 只能放视频字段 |
| `material_not_found` | ID 错误、已删除或不属于当前用户/站点 |
| `material_account_unavailable` | 原素材账户被停用或改动；恢复账户或重新创建素材 |
| `material_group_not_verified` | 真人认证组尚未完成认证；继续查询认证结果 |
| `material_group_not_empty` | 先删除分组内素材，再删除分组 |
| `DownloadFailed` | 源 URL 无法公开下载；检查有效期、防盗链、权限和响应类型 |

其他错误见 [常见报错与处理](troubleshooting.md)。生成任务仍按所选 Seedance 型号实际计费；不要为验证同一能力重复提交付费任务。
