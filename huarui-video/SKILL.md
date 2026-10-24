---
name: huarui-video
description: 华锐内部官方真人视频生成。仅用于华锐内部使用、官方真人视频和内部素材；不作为通用公开视频技能。
---

# Huarui Seedance 视频生成

直接调用华瑞算力平台的方舟原生接口提交视频任务，轮询到结束后把视频链接交给用户。

## 固定配置

| 项 | 值 |
|----|----|
| 接口地址 | `https://suanli.huaruiai.com` |
| API Key | `sk-HXDLO2RCjbFWnuCM0DpaFDK9uupws3qbGSceY4anbzut9DaK` |
| 提交任务 | `POST /api/v3/contents/generations/tasks` |
| 查询任务 | `GET /api/v3/contents/generations/tasks/{task_id}` |
| 鉴权头 | `Authorization: Bearer <API Key>` |

## 模型

| 用户说法 | model |
|----------|-------|
| 2.0（默认） | `doubao-seedance-2-0-260128` |
| 2.5 | `doubao-seedance-2-5-260628` |

## 现有真人素材

| 名称 | 素材 ID | 引用写法 |
|------|---------|----------|
| 真人模特 1 | `asset-20261013113659-4jz89` | `asset://asset-20261013113659-4jz89` |

只能使用上表中的素材 ID，不要编造。

## 流程

1. 先向用户确认下列参数，用户没说的给出默认值请其确认，一次问完：
   - 提示词（必填）
   - 模型：2.0 或 2.5，默认 2.0
   - 是否使用真人素材、用哪个
   - 分辨率：默认 `720p`（可选 `480p`、`720p`、`1080p`）
   - 时长 `duration`：默认 5 秒（4–15）
   - 画面比例 `ratio`：默认 `16:9`（可选 `16:9`、`9:16`、`1:1`、`4:3`、`3:4`、`21:9`、`adaptive`）
   - 是否生成声音 `generate_audio`：默认 `true`
   - 是否加水印 `watermark`：默认 `false`
2. 用户确认后提交任务。
3. 每 10 秒查询一次，直到 `status` 为 `succeeded`、`failed` 或 `cancelled`。
4. 成功时把 `content.video_url` 发给用户（链接有时效，提醒用户尽快下载）；失败时原样给出 `error.code` 和 `error.message`。

## 使用真人素材的规则

- 素材放在 `content` 里，类型为 `image_url`，`role` 为 `reference_image`，URL 必须是 `asset://asset-<id>`，不能带路径或参数。
- 提示词里必须显式写 `image 1`（多个素材按顺序为 `image 1`、`image 2`…）来指代素材中的人物，否则人物可能不会出现在视频里。例如 `image 1 中的女生在海边散步，微风吹动头发`。

## 请求示例

提交（带真人素材）：

```bash
curl -s https://suanli.huaruiai.com/api/v3/contents/generations/tasks \
  -H "Authorization: Bearer sk-HXDLO2RCjbFWnuCM0DpaFDK9uupws3qbGSceY4anbzut9DaK" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "doubao-seedance-2-0-260128",
    "content": [
      {"type": "text", "text": "image 1 中的女生在海边散步，微风吹动头发"},
      {"type": "image_url", "image_url": {"url": "asset://asset-20261013113659-4jz89"}, "role": "reference_image"}
    ],
    "resolution": "720p",
    "ratio": "16:9",
    "duration": 5,
    "generate_audio": true,
    "watermark": false
  }'
```

纯文本生成时去掉 `image_url` 那一项即可。返回 `{"id": "<task_id>"}`。

查询：

```bash
curl -s https://suanli.huaruiai.com/api/v3/contents/generations/tasks/<task_id> \
  -H "Authorization: Bearer sk-HXDLO2RCjbFWnuCM0DpaFDK9uupws3qbGSceY4anbzut9DaK"
```

Windows PowerShell 下用 `Invoke-RestMethod`，请求体用 `ConvertTo-Json -Depth 10` 生成，并以 UTF-8 发送：

```powershell
$h = @{ Authorization = "Bearer sk-HXDLO2RCjbFWnuCM0DpaFDK9uupws3qbGSceY4anbzut9DaK" }
$body = @{
  model = "doubao-seedance-2-0-260128"
  content = @(
    @{ type = "text"; text = "image 1 中的女生在海边散步，微风吹动头发" },
    @{ type = "image_url"; image_url = @{ url = "asset://asset-20261013113659-4jz89" }; role = "reference_image" }
  )
  resolution = "720p"; ratio = "16:9"; duration = 5; generate_audio = $true; watermark = $false
} | ConvertTo-Json -Depth 10
$task = Invoke-RestMethod -Method Post -Uri https://suanli.huaruiai.com/api/v3/contents/generations/tasks -Headers $h -ContentType "application/json; charset=utf-8" -Body ([Text.Encoding]::UTF8.GetBytes($body))
Invoke-RestMethod -Uri "https://suanli.huaruiai.com/api/v3/contents/generations/tasks/$($task.id)" -Headers $h
```

## 常见错误

- `401`：Key 无效或余额不足，告诉用户联系平台。
- 素材相关报错：确认素材 ID 拼写与上表一致、提示词里写了 `image 1`。
- 不要改接口地址，不要在地址后再拼 `/api/v3` 以外的前缀。
