# HappyHorse 与 Wan 视频

先设置 SKILL.md 中的环境变量。以下型号创建后都使用 `GET /v1/videos/{id}` 查询，完成后使用 `GET /v1/videos/{id}/content` 下载。

## 1. 文字生成视频

`happyhorse-1.1-t2v` 与 `wan3.0-video-prime` 使用以下文字生成格式。示例为 5 秒、1280×720：

```bash
curl --silent --show-error --fail-with-body \
  "$JUHE_BASE_URL/v1/videos" \
  -H "Authorization: Bearer $JUHE_API_KEY" \
  -H 'Content-Type: application/json' \
  --data '{
    "model": "happyhorse-1.1-t2v",
    "prompt": "清晨柔和阳光中的安静花园，镜头缓慢移动，无字幕。",
    "seconds": "5",
    "size": "1280*720"
  }'
```

将 `model` 替换为 `wan3.0-video-prime` 可使用同一请求格式。`size` 在此使用星号 `*`；不要直接套用图片接口的尺寸写法。

## 2. 图片生成视频

`happyhorse-1.1-i2v` 使用 `image` 提供可访问的参考图片 URL，`size` 使用 `"720P"`。

```bash
curl --silent --show-error --fail-with-body \
  "$JUHE_BASE_URL/v1/videos" \
  -H "Authorization: Bearer $JUHE_API_KEY" \
  -H 'Content-Type: application/json' \
  --data '{
    "model": "happyhorse-1.1-i2v",
    "prompt": "保留参考图中的主体与场景，镜头缓慢推进，自然光，无字幕。",
    "image": "https://example.com/reference.png",
    "seconds": "5",
    "size": "720P"
  }'
```

## 3. 查询与下载

保存创建响应的 `id`：

```bash
export TASK_ID='task_your_id'

curl --silent --show-error --fail-with-body \
  "$JUHE_BASE_URL/v1/videos/$TASK_ID" \
  -H "Authorization: Bearer $JUHE_API_KEY"
```

`queued`、`in_progress` 时每隔约 10 秒查询一次；`completed` 后下载；`failed` 时读取错误并停止轮询。

```bash
curl --silent --show-error --fail-with-body --location \
  "$JUHE_BASE_URL/v1/videos/$TASK_ID/content" \
  -H "Authorization: Bearer $JUHE_API_KEY" \
  --output video.mp4
```

## 4. 其他 HappyHorse 型号

### 参考图片生成

`happyhorse-1.1-r2v` 的参考元素类型使用 `reference_image`，通过 `input.media` 提交：

```bash
curl --silent --show-error --fail-with-body \
  "$JUHE_BASE_URL/v1/videos" \
  -H "Authorization: Bearer $JUHE_API_KEY" \
  -H 'Content-Type: application/json' \
  --data '{
    "model": "happyhorse-1.1-r2v",
    "prompt": "保留参考图中的主体，镜头缓慢移动，无字幕。",
    "seconds": "5",
    "size": "720P",
    "input": {"media": [{"type": "reference_image", "url": "https://example.com/reference.png"}]}
  }'
```

查询与下载方法同上。

### 编辑已有视频

`happyhorse-1.0-video-edit` 的源视频类型使用 `video`：

```bash
curl --silent --show-error --fail-with-body \
  "$JUHE_BASE_URL/v1/videos" \
  -H "Authorization: Bearer $JUHE_API_KEY" \
  -H 'Content-Type: application/json' \
  --data '{
    "model": "happyhorse-1.0-video-edit",
    "prompt": "把光线改成温暖的夕阳色调，保留主体和运镜。",
    "seconds": "5",
    "size": "720P",
    "input": {"media": [{"type": "video", "url": "https://example.com/source.mp4"}]}
  }'
```

源视频 URL 必须能被远端读取，并在处理期间保持有效。遇到错误时见 [常见报错与处理](troubleshooting.md)。
