# Seedance 参数与 curl 示例

以下示例先执行 SKILL.md 中的环境变量设置。示例默认生成 5 秒、720p 视频；参考图片和视频地址需替换为实际可访问的 HTTPS URL。

| 型号                | `model`                           |
| ----------------- | --------------------------------- |
| Seedance 2.0      | `doubao-seedance-2-0-260128`      |
| Seedance 2.0 Fast | `doubao-seedance-2-0-fast-260128` |
| Seedance 2.0 Mini | `doubao-seedance-2-0-mini-260615` |
| Seedance 2.5      | `doubao-seedance-2-5-260628`      |

两种创建格式任选一种；同一需求只提交一次。遇到错误时见 [常见报错与处理](troubleshooting.md)。

## 1. 方舟格式参数

使用 `POST /api/v3/contents/generations/tasks`，请求体为 JSON。

| 字段               | 类型        | 说明                                       |
| ---------------- | --------- | ---------------------------------------- |
| `model`          | string，必填 | 上表中的完整型号 ID                              |
| `content`        | array，必填  | 文字和参考输入列表                                |
| `duration`       | integer   | 输出时长，单位秒，例如 `5`                          |
| `resolution`     | string    | 输出分辨率，例如 `"720p"`                        |
| `ratio`          | string    | 画面比例，例如 `"16:9"`、`"9:16"` 或 `"adaptive"` |
| `generate_audio` | boolean   | 是否生成声音                                   |
| `watermark`      | boolean   | 是否添加水印                                   |

布尔值使用 `true` / `false`，不要写成字符串。提示词放在 `content` 中的 `text` 元素；图片和视频分别使用 `image_url`、`video_url` 元素。

## 2. 文字生成视频

```bash
curl --silent --show-error --fail-with-body \
  "$JUHE_BASE_URL/api/v3/contents/generations/tasks" \
  -H "Authorization: Bearer $JUHE_API_KEY" \
  -H 'Content-Type: application/json' \
  --data '{
    "model": "doubao-seedance-2-0-260128",
    "content": [
      {"type": "text", "text": "清晨阳光下，一只橘猫走过开满鲜花的庭院，镜头缓慢跟随，暖色调，自然光，5秒完整镜头，无字幕。"}
    ],
    "duration": 5,
    "resolution": "720p",
    "ratio": "16:9",
    "generate_audio": true,
    "watermark": false
  }'
```

创建成功后，保存响应中的 `id`。以下为关键字段示意：

```json
{"id":"task_your_id"}
```

## 3. 图片参考生成视频

参考图片使用 `role: "reference_image"`。URL 必须能被远端读取，并在排队和生成期间保持有效。

```bash
curl --silent --show-error --fail-with-body \
  "$JUHE_BASE_URL/api/v3/contents/generations/tasks" \
  -H "Authorization: Bearer $JUHE_API_KEY" \
  -H 'Content-Type: application/json' \
  --data '{
    "model": "doubao-seedance-2-0-260128",
    "content": [
      {"type": "text", "text": "保持参考图中产品的外观和配色，产品置于简洁展台，镜头缓慢环绕，柔和棚拍光，5秒，无字幕。"},
      {"type": "image_url", "image_url": {"url": "https://example.com/product.jpg"}, "role": "reference_image"}
    ],
    "duration": 5,
    "resolution": "720p",
    "ratio": "16:9",
    "watermark": false
  }'
```

需要首帧或尾帧输入时，图片元素的 `role` 分别为 `first_frame`、`last_frame`，按所选型号允许的组合提交。

## 4. 视频参考生成视频

参考视频使用 `role: "reference_video"`。

```bash
curl --silent --show-error --fail-with-body \
  "$JUHE_BASE_URL/api/v3/contents/generations/tasks" \
  -H "Authorization: Bearer $JUHE_API_KEY" \
  -H 'Content-Type: application/json' \
  --data '{
    "model": "doubao-seedance-2-0-260128",
    "content": [
      {"type": "text", "text": "参考视频中的运镜与运动节奏，生成海边日落场景，镜头平稳前进，暖色调，5秒，无字幕。"},
      {"type": "video_url", "video_url": {"url": "https://example.com/reference.mp4"}, "role": "reference_video"}
    ],
    "duration": 5,
    "resolution": "720p",
    "ratio": "adaptive",
    "watermark": false
  }'
```

## 5. 查询与下载

把创建响应中的真实 `id` 填入 `TASK_ID`，不要使用示例占位值。

```bash
export TASK_ID='task_your_id'

curl --silent --show-error --fail-with-body \
  "$JUHE_BASE_URL/api/v3/contents/generations/tasks/$TASK_ID" \
  -H "Authorization: Bearer $JUHE_API_KEY"
```

| `status`    | 含义                               |
| ----------- | -------------------------------- |
| `queued`    | 排队中                              |
| `running`   | 生成中                              |
| `succeeded` | 已完成，从 `content.video_url` 获取成片地址 |
| `failed`    | 失败，查看 `error.message`            |

`queued`、`running` 时继续间隔查询；`succeeded`、`failed` 时停止轮询。成功响应关键字段示意：

```json
{
  "id": "task_your_id",
  "status": "succeeded",
  "content": {"video_url": "https://example.com/result.mp4"}
}
```

完成后使用同一任务 ID 下载：

```bash
curl --silent --show-error --fail-with-body --location \
  "$JUHE_BASE_URL/v1/videos/$TASK_ID/content" \
  -H "Authorization: Bearer $JUHE_API_KEY" \
  --output seedance.mp4
```

也可使用响应中的 `content.video_url` 下载成片。成片链接可能过期，完成后及时保存。

## 6. OpenAI Video 格式

文字生成使用 `prompt`，时长通过字符串 `seconds` 传入，画面参数放在 `metadata` 中。

```bash
curl --silent --show-error --fail-with-body \
  "$JUHE_BASE_URL/v1/videos" \
  -H "Authorization: Bearer $JUHE_API_KEY" \
  -H 'Content-Type: application/json' \
  --data '{
    "model": "doubao-seedance-2-0-mini-260615",
    "prompt": "清晨薄雾中的山间茶园，镜头缓慢向前，柔和自然光，5秒，无字幕。",
    "seconds": "5",
    "metadata": {
      "resolution": "720p",
      "ratio": "16:9",
      "generate_audio": true,
      "watermark": false
    }
  }'
```

需要参考输入时，在 `metadata.content` 中同时写入文字与媒体元素，顶层 `prompt` 填写同一段文字。例如：

```bash
curl --silent --show-error --fail-with-body \
  "$JUHE_BASE_URL/v1/videos" \
  -H "Authorization: Bearer $JUHE_API_KEY" \
  -H 'Content-Type: application/json' \
  --data '{
    "model": "doubao-seedance-2-0-260128",
    "prompt": "保持参考图中产品的外观，镜头缓慢环绕展台，柔和棚拍光，5秒，无字幕。",
    "seconds": "5",
    "metadata": {
      "content": [
        {"type": "text", "text": "保持参考图中产品的外观，镜头缓慢环绕展台，柔和棚拍光，5秒，无字幕。"},
        {"type": "image_url", "image_url": {"url": "https://example.com/product.jpg"}, "role": "reference_image"}
      ],
      "resolution": "720p",
      "ratio": "16:9",
      "watermark": false
    }
  }'
```

保存创建响应的 `id`，随后查询：

```bash
export TASK_ID='task_your_id'

curl --silent --show-error --fail-with-body \
  "$JUHE_BASE_URL/v1/videos/$TASK_ID" \
  -H "Authorization: Bearer $JUHE_API_KEY"
```

此格式的状态为 `queued`、`in_progress`、`completed`、`failed`。`completed` 后，按第 5 节使用 `/v1/videos/{id}/content` 下载。
