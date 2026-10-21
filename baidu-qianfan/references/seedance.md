# FireSeries Seedance 视频

## 模型

| 能力 | FireSeries 模型 |
| --- | --- |
| Seedance 2.0 | `S2.0` |
| Seedance 2.0 Fast | `S2.0-Fast` |
| Seedance 2.0 Mini | `S2.0-Mini` |
| Seedance 2.5 | `S2.5` |

## 创建任务

```bash
curl --fail-with-body -sS "$BAIDU_QF_URL/beta/video/generations/qianfan-video/fireseries" \
  -H "Authorization: Bearer $BAIDU_QF_KEY" \
  -H 'Content-Type: application/json' \
  --data '{
    "model": "S2.0-Mini",
    "content": [{"type": "text", "text": "生成一段简洁的自然风景短视频"}],
    "duration": 5,
    "resolution": "720p",
    "ratio": "16:9"
  }'
```

创建响应中的任务 ID 位于 `data.task_id`。

## 查询任务

```bash
curl --fail-with-body -sS \
  "$BAIDU_QF_URL/beta/video/generations/qianfan-video/fireseries?task_id=$TASK_ID" \
  -H "Authorization: Bearer $BAIDU_QF_KEY"
```

## 参考媒体

```json
{
  "type": "image_url",
  "image_url": {"url": "https://example.com/reference.png"},
  "role": "reference_image"
}
```

视频与音频使用 `video_url` / `audio_url`，角色分别为 `reference_video` / `reference_audio`。