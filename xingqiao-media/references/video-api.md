# 星桥 · 视频接口备忘

来源：服务方《视频 API · 第三方对接文档》2026-10-26 版，只保留调用要用的部分。服务地址 `https://api.novqiao.com`。

保留供应商原始 `cost_usd` 字段与报价币种；实际结算币种和换算比例由当前账号合约及账单确认，不默认 1:1。报价不锁价。


`/v1/video-v2/*` 与 `/v1/videos*` 是两套协议，ID、字段、状态机都不能混用，旧接口不会重定向到新协议。本项目只用 video-v2。

## 接口

| 方法 | 路径 | 结果 |
|---|---|---|
| GET | `/v1/video-v2/models` | 模型、时长、素材能力与价格 |
| POST | `/v1/video-v2/references` | multipart 上传素材，200 |
| POST | `/v1/video-v2/tasks` | 建任务，202 |
| GET | `/v1/video-v2/tasks/{task_id}` | 单查 |
| POST | `/v1/video-v2/tasks/query` | 批量查，`{"task_ids":["vid_1"]}`，上限 100 |
| GET | `/v1/video-v2/tasks/{task_id}/content` | 原 Key 下载，307 |
| GET | `/v1/media/callbacks/signing-key` | 与图片共用验签密钥 |

## 模型目录

`{"items":[...]}`，用 `items[].id` 作 `model`，**不要用 `name`**。

| 字段 | 用途 |
|---|---|
| `id`、`name`、`enabled`、`disabled_reason` | 可用性 |
| `ratios`、`resolutions` | 允许的比例与分辨率 |
| `duration_options` | 按分辨率索引的秒数数组，不要只看 `max_duration` |
| `reference_video_duration_options` | 带参考视频时的可选时长 |
| `generation_modes`、`input_capabilities` | 首尾帧、提示词增强等 |
| `max_images`／`max_audios`／`max_videos`／`max_video_audios` | 附件上限，0 表示不收 |
| `estimated_costs` | 按分辨率／秒数索引的预计费用 |
| `reference_video_estimated_costs` | 带参考视频时优先用这张 |
| `billing_variants`、`reference_video_prices_per_second`、`reference_video_multipliers` | 特殊计费 |

缺价不能按 0 处理；明确返回数值 0 才是免费。目录不锁价，最终看 `cost_usd`。

## 创建任务字段

| 字段 | 要求 |
|---|---|
| `client_task_id` | 稳定业务 ID，≤160 UTF-8 字节 |
| `model` | 目录里的完整 `id` |
| `prompt` | 非空，≤5000 字符 |
| `duration` | 整数秒，必须在该模型对应分辨率的 `duration_options` 里 |
| `ratio`、`resolution` | 来自目录，建议显式传 |
| `image_urls` | 参考图 URL；首尾帧模式按首帧、尾帧顺序 |
| `audio_urls`／`video_urls`／`video_audio_urls` | 仅模型允许时传 |
| `mode` | 如 `first_last_frame`，需模型声明；要求恰好两张图且不混音视频 |
| `prompt_enhance` | 布尔，仅支持增强的模型可传 |
| `workflow`／`size` | 个别模型专用，不能代替 `resolution` |
| `megapixels` | 仅目录开放时传；`priority` 当前不接受 |
| `callback_url` | 可选公网 HTTPS |

**未知字段直接 400**，别把图片接口的参数抄过来。参考素材须服务端可访问，外部链接要 HTTPS 且不能指向本机或私网。

## 去重规则（重要）

同一 Key + 同一 `client_task_id` 只对应同一任务，重复提交返回原任务、不再生成、不二次扣费。**沿用首次提交的参数**——即使第二次正文不同，也不修改原任务。

改提示词、换模型、换素材重新生成时，必须用新的业务 ID。

省略 `client_task_id` 时可用 `Idempotency-Key` 作业务 ID（1–128 可打印 ASCII）；两者同时存在以正文为准。视频去重靠已存任务，没有图片那种 24 小时窗口。

## 上传素材

```bash
curl -X POST 'https://api.novqiao.com/v1/video-v2/references' \
  -H 'Authorization: Bearer sk-...' -F 'kind=image' -F 'file=@reference.png'
```

`kind` 取 `image`／`audio`／`video`。图片 ≤10 MiB，音频／视频 ≤50 MiB。返回 `{"url","resource_id","name","mime_type","size","kind"}`，**创建任务用 `url` 放进对应数组**，`resource_id` 部分存储方式下不返回。素材 URL 有时效，别当长期资产存档。

## 状态机

| status／提示 | 动作 |
|---|---|
| `queued`、`running` | 继续查同一任务 |
| `state:saving` | 生成结束、仍在保存，继续查 |
| `succeeded` + `next_action:save_resource` | 归档未完成，继续查 |
| `succeeded` + `next_action:read_result` | 读 `data` 下载 |
| `failed` | 记 `error.code`／`stage`／`message`，停止自动重提 |

`progress` 不保证连续，别用它推算剩余时间。`terminal:true` 但 `next_action:save_resource` 仍要继续查。

已保存结果：

```json
{"task_id":"vid_...","client_task_id":"...","status":"succeeded","terminal":true,
 "next_action":"read_result","resource_status":"completed","resource_id":31,
 "cost_usd":0.8,
 "data":[{"url":"/v1/video-v2/tasks/vid_.../content","mime_type":"video/mp4",
 "size_bytes":1048576,"download_url":"https://.../v1/image-v2/images/31/download?ticket=...",
 "url_expires_at":1793048400}]}
```

## 两种下载

1. **原方式**：相对 `data[].url` 拼成绝对地址，带原 Key GET，`/content` 返回 307 再跟。**不要把 Bearer 转发到存储域**（`xq.py` 的重定向处理会摘掉 Authorization）。
2. **新方式**：有 `download_url` 直接 GET，无需 Key，24 小时有效。路径可能含 `image-v2`，内容仍是视频。

链接过期用原 Key 重新查任务，**不重新生成**。部分历史结果 `url` 是外部成品地址，按实际值用。

## 错误

| HTTP／code | 处理 |
|---|---|
| 400 `VIDEO_REQUEST_INVALID` | 查字段名、JSON、类型，不传未知字段 |
| 400 `VIDEO_CLIENT_TASK_ID_INVALID` | 检查业务 ID，已有请求保留原 ID |
| 400 参数／素材错误 | 重读目录改组合 |
| 401／403 | Key、分组、模型、钱包额度 |
| 404 `VIDEO_TASK_NOT_FOUND` | 核字符串 ID 与原 Key |
| `VIDEO_NOT_READY` | 尚未可下载，继续查 |
| 429／503 | 按提示退避，恢复提交用同一业务 ID |
| 受理结果不确定 | 保留任务与业务 ID，不换 ID 不重提，找服务方核查 |

网络断开时用相同 Key、相同 `client_task_id`、原参数恢复。**HTTP 超时 ≠ 没扣费、没生成。**

## 回调（按当前任务选择并授权部署）

外层 `{"event":"video_task.completed","task":{...}}`，失败为 `video_task.failed`，`task.error` 带 `code`／`stage`／`message`。至少一次，最多 8 次。按 `X-Sub2API-Idempotency-Key` 去重，10 秒内回 2xx。验签算法与图片一致，图片视频共用同一验签密钥。
