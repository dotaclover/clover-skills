# FireSeries Seedance 视频任务

FireSeries 是异步付费任务。只有用户明确批准付费生成时，才创建任务；提交后要一直查询到终态。

## 模型和端点

| 目标能力 | FireSeries 模型 |
| --- | --- |
| Seedance 2.0 | `S2.0` |
| Seedance 2.0 Fast | `S2.0-Fast` |
| Seedance 2.0 Mini | `S2.0-Mini` |
| Seedance 2.5 | `S2.5` |

```text
POST {BAIDU_QF_URL}/beta/video/generations/qianfan-video/fireseries
GET  {BAIDU_QF_URL}/beta/video/generations/qianfan-video/fireseries?task_id={task_id}
Authorization: Bearer <BAIDU_QF_KEY>
```

## 最小文本生成示例

```bash
# 会产生费用：仅在得到明确授权后执行
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

成功创建响应通常含 `data.task_id`。保存该 ID 到私有系统后查询：

```bash
curl --fail-with-body -sS \
  "$BAIDU_QF_URL/beta/video/generations/qianfan-video/fireseries?task_id=$TASK_ID" \
  -H "Authorization: Bearer $BAIDU_QF_KEY"
```

等待实际响应中的成功或失败终态。任务处理中、排队中或未知状态都不是完成。

## 参考媒体

输入媒体使用上游可访问的 URL，并按素材类型标注角色：

```json
{
  "type": "image_url",
  "image_url": {"url": "https://example.com/reference.png"},
  "role": "reference_image"
}
```

视频和音频对应 `video_url` / `audio_url` 及 `reference_video` / `reference_audio`。支持的素材数量、首尾帧、音频、分辨率和比例取决于模型与当前账号能力；在上线前用最小任务逐项验证。

\n