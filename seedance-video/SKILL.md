---
name: seedance-video
description: 直接调用火山方舟（Volcengine Ark）Seedance API 生成视频。支持 Seedance 2.5 / 2.0 系列的文生视频、图生视频（首帧/首尾帧）、多模态参考（图片+视频+音频）、视频编辑与延长，含任务提交、轮询、成片下载。当用户要求"生成视频""Seedance""即梦视频""豆包视频生成"时使用。
agent_created: true
---

# 火山方舟 Seedance 视频生成

直接调用火山方舟官方 API（异步任务模式：提交 → 轮询 → 下载成片）。

## 前置条件

- API Key：`Authorization: Bearer $ARK_API_KEY`（方舟控制台 API Key 管理页获取）。
- Base URL：`https://ark.cn-beijing.volces.com/api/v3`（Agent Plan 企业版专属为 `/api/plan/v3`，model 用 `doubao-seedance-2.0` 简写）。
- 开通条件：账户余额 > 200 元，或已购 200 元档及以上节省计划，或有余量的 Seedance 资源包。

## 接口

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| POST | `/contents/generations/tasks` | 创建视频生成任务 |
| GET | `/contents/generations/tasks/{id}` | 查询任务状态与成片 |
| GET | `/contents/generations/tasks?filter.status=...&filter.task_ids=...&filter.model=...` | 批量查询（近 7 天） |
| DELETE | `/contents/generations/tasks/{id}` | 取消（仅 queued）/删除任务 |

## 模型 ID

| 模型 | Model ID | 分辨率 | 时长 |
| --- | --- | --- | --- |
| Seedance 2.5 | `doubao-seedance-2-5-260628` | 480p / 720p（无 1080p/4K） | 4–30 秒，或 `-1` 智能决定 |
| Seedance 2.0 | `doubao-seedance-2-0-260128` | 480p / 720p / 1080p / 4K(10bit) | 4–15 秒 |
| Seedance 2.0 Fast | `doubao-seedance-2-0-fast-260128` | 480p / 720p | 4–15 秒 |
| Seedance 2.0 Mini | `doubao-seedance-2-0-mini-260615` | 480p / 720p | 4–15 秒（最低成本） |

## 请求体

```json
{
  "model": "doubao-seedance-2-5-260628",
  "content": [
    { "type": "text", "text": "女孩抱着狐狸，睁开眼温柔地看向镜头，镜头缓缓拉出，可以听到风声" },
    { "type": "image_url", "role": "first_frame", "image_url": { "url": "https://example.com/first.png" } }
  ],
  "duration": 5,
  "resolution": "720p",
  "ratio": "adaptive",
  "generate_audio": true,
  "watermark": false
}
```

### content 元素

| type | role | 说明 |
| --- | --- | --- |
| `text` | — | 提示词；口语台词用双引号包裹可引导生成对应语音 |
| `image_url` | `first_frame` / `last_frame` / `reference_image` | 首帧、尾帧、参考图 |
| `video_url` | `reference_video` | 参考视频 |
| `audio_url` | `reference_audio` | 参考音频 |

### 素材限制（三种场景互斥，不可混用）

| 素材 | 2.0 系列 | 2.5 |
| --- | --- | --- |
| 参考图 | 1–9 张 | 最多 30 张 |
| 参考视频 | ≤3 个，总时长 ≤15s，单个 2–30s | ≤10 个，单个 2–30s，合计 ≤30s |
| 参考音频 | ≤3 段，总时长 ≤15s，**不可纯音频** | ≤10 段，合计 ≤30s，**支持纯音频生成** |
| 单次总量 | ≤12 | ≤50（30 图 + 10 视频 + 10 音频） |

- 首帧 / 首尾帧 / 多模态参考为三种互斥模式；尾帧必须搭配首帧。
- 使用 first_frame/last_frame 时 ratio 强制 `adaptive`；视频编辑/延长任务 duration 仅支持 `-1`、ratio 仅支持 `adaptive`。

### 其他参数

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `duration` | 5 | 秒；`-1` 由模型决定（2.5，编辑/延长必为 -1） |
| `resolution` | 720p | 480p / 720p / 1080p / 4K（4K 仅 2.0 标准版） |
| `ratio` | 16:9（2.5 也可 adaptive） | 21:9, 16:9, 4:3, 1:1, 3:4, 9:16 |
| `generate_audio` | 2.5 为 true，2.0 需显式开 | 有声视频（语音/音效/BGM） |
| `watermark` | false | 右下角"AI生成"标记 |
| `seed` | -1 | 随机种子 |
| `camera_fixed` | false | 固定摄像头 |
| `return_last_frame` | false | 返回尾帧图（用于跨段连续生成） |
| `output_format` | mp4 | mp4 / mov（mov 仅 2.5） |
| `callback_url` | — | 状态变化回调 |
| `execution_expires_after` | 172800 | 任务超时秒数 |

注意：参考素材**不能包含真人面部**（2.0 与 2.5 均受限）。

## 执行步骤（Agent 使用）

1. 提交任务：`POST /contents/generations/tasks`，拿到 `id`（格式 `cgt-...`）。
2. 轮询：`GET /contents/generations/tasks/{id}`，间隔 10–30 秒。状态流转 `queued → running → succeeded / failed`（`cancelled` 仅 queued 可取消，24h 自动删除）。
3. `succeeded` 后从 `content.video_url` 下载成片。**视频 URL 有效期仅 24 小时**（2.5 下载次数上限 100 次），必须立即下载转存，不能把 URL 当长期结果地址。
4. 任务记录仅保留 7 天。
5. 用 present_files 展示下载到本地的视频文件。

### curl 示例

```bash
# 创建
curl -s https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ARK_API_KEY" \
  -d '{"model":"doubao-seedance-2-5-260628","content":[{"type":"text","text":"..."}],"duration":10,"resolution":"720p","generate_audio":true}'

# 轮询
curl -s https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks/$TASK_ID \
  -H "Authorization: Bearer $ARK_API_KEY"
```

### 成功响应（轮询）

```json
{
  "id": "cgt-20260414114820-****",
  "model": "doubao-seedance-2-0-260128",
  "status": "succeeded",
  "content": { "video_url": "https://...", "last_frame_url": null },
  "usage": { "completion_tokens": 411300, "total_tokens": 411300 },
  "duration": 11, "resolution": "720p", "ratio": "16:9",
  "framespersecond": 24, "seed": 33608
}
```

计费按 usage tokens（与时长/分辨率相关），以任务完成后 usage 为准。
