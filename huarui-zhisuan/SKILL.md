---
name: huarui-zhisuan
description: 调用华锐智算的 Seedance 视频与素材 API，提供接口端点、API Key 鉴权、支持型号、请求参数、curl 示例和错误处理。适用于文生视频、参考素材生成、任务查询下载及账号私有素材管理。
agent_created: true
---

# 华锐智算 Seedance API

## 1. 服务地址与鉴权

| 项目 | 值 |
|---|---|
| Base URL | `https://suanli.huaruiai.com` |
| 鉴权方式 | 请求头 `Authorization: Bearer <API Key>` |
| 请求格式 | `Content-Type: application/json` |

服务仅接受 HTTPS。使用 `http://` 会收到 `301` 跳转到 HTTPS；客户端跟随跳转时会把 POST 降级为 GET，所有写接口因此返回 `404 {"error":{"message":"Invalid URL (GET ...)"}}`，素材接口 `/?Action=...` 则返回前端页面。接口层正常响应必为 `application/json`，收到 `text/html` 说明请求未进入接口层，与 Key、权限、余额无关。

HTTPS 使用受信任证书，无需关闭证书校验。

## 2. 支持型号

| 型号 | model |
|---|---|
| Seedance 2.0（默认） | `doubao-seedance-2-0-260128` |
| Seedance 2.0 Fast | `doubao-seedance-2-0-fast-260128` |
| Seedance 2.0 Mini | `doubao-seedance-2-0-mini-260615` |
| Seedance 2.5 | `doubao-seedance-2-5-260628` |

可用型号以当前 API Key 的权限为准，通过 `GET /v1/models` 查询。其他型号的时长、分辨率与参考素材组合以该型号支持范围为准。

## 3. 端点

| 功能 | 方法与路径 | 备注 |
|---|---|---|
| 创建视频（火山方舟格式） | `POST /api/v3/contents/generations/tasks` | 推荐 |
| 查询视频（火山方舟格式） | `GET /api/v3/contents/generations/tasks/{id}` | |
| 创建视频（OpenAI Video 格式） | `POST /v1/videos` | 与上一格式二选一 |
| 查询视频（OpenAI Video 格式） | `GET /v1/videos/{id}` | |
| 下载视频 | `GET /v1/videos/{id}/content` | |
| 素材组与素材的增删改查 | `POST /?Action={Action}&Version=2024-01-01` | |
| 真人授权会话与结果查询 | 同上，Action 为 `CreateVisualValidateSession` / `GetVisualValidateResult` | 需服务方开通 |

两种视频格式任选一种创建，同一视频不要分别提交。视频支持文字、图片、视频、音频参考，组合方式以所选型号为准。素材按账号隔离，通过 `asset://` 引用本人素材。

## 4. 快速开始

```bash
export HUARUI_BASE_URL='https://suanli.huaruiai.com'
read -rsp 'API Key: ' HUARUI_API_KEY; echo
export HUARUI_API_KEY

curl --silent --show-error --fail-with-body \
  "$HUARUI_BASE_URL/api/v3/contents/generations/tasks" \
  -H "Authorization: Bearer $HUARUI_API_KEY" \
  -H 'Content-Type: application/json' \
  --data '{"model":"doubao-seedance-2-0-mini-260615","content":[{"type":"text","text":"<提示词>"}],"duration":5,"resolution":"720p","ratio":"16:9","generate_audio":true,"watermark":false}'
```

创建成功返回任务 ID：

```json
{"id":"task_xxx"}
```

随后每 10 秒查询一次任务，`status` 变为 `succeeded` 后从 `content.video_url` 下载：

```bash
curl --silent --show-error --fail-with-body \
  "$HUARUI_BASE_URL/api/v3/contents/generations/tasks/$TASK_ID" \
  -H "Authorization: Bearer $HUARUI_API_KEY"
```

`5` 秒 720p 任务通常 2–3 分钟完成。`content.video_url` 为带签名的临时链接，有效期 24 小时，须立即下载保存。

## 5. 请求参数

| 参数 | 类型 | 说明 |
|---|---|---|
| `model` | string，必填 | 第 2 节中的完整型号 ID |
| `content` | array，必填 | 文字与参考素材列表，元素格式见参考文档第 5 节 |
| `duration` | integer | 输出时长，单位秒 |
| `resolution` | string | 输出分辨率，例如 `"720p"` |
| `ratio` | string | 画面比例，例如 `"16:9"` |
| `generate_audio` | boolean | 是否生成声音 |
| `watermark` | boolean | 是否添加水印 |

布尔值使用 JSON 的 `true` / `false`，不要写成字符串。

成功响应的关键字段：

| 字段 | 说明 |
|---|---|
| `content.video_url` | 成片地址，带签名，24 小时有效 |
| `duration` / `resolution` / `ratio` / `framespersecond` | 实际输出规格 |
| `usage.completion_tokens` | 用量，用于核对计费 |
| `upstream_id` | 上游任务号，报障时提供 |

## 6. 提示词规范

提示词决定成片质量，也决定是否通过内容审核。结构建议：风格 + 主体 + 动作 + 环境 + 光线色调 + 镜头运动 + 时长与画面要求。

**不得在提示词中点名作品、工作室、导演或"某某风格"。** 此类描述会触发版权审核，任务以 `failed` 结束：

```json
{
  "status": "failed",
  "error": {"message": "The request failed because the output video may be related to copyright restrictions. Request id: ..."}
}
```

改写原则：把风格意图翻译为画面语言，角色与场景一律原创。

| 避免 | 改为 |
|---|---|
| 吉卜力风格 / 宫崎骏风格 / 某动画电影风格 | 原创手绘水彩插画风格，2D 赛璐璐上色，水彩晕染背景 |
| 某知名 IP 角色 | 原创角色：扎双马尾的少女，白色连衣裙 |
| 复刻某导演镜头语言 | 镜头从侧面缓慢横移并轻轻推近 |

符合规范的提示词示例：

```text
原创手绘水彩插画风格，治愈系夏日乡野。一个扎双马尾的原创少女站在青草山坡上，
白色连衣裙被风吹起，她伸手按住草帽；天空湛蓝飘着大朵积云，远处红色屋顶的小屋和一棵大树，
草浪随风起伏，空中飘着白色绒絮，暖色调柔和光线，水彩晕染质感，
镜头从侧面缓慢横移并轻轻推近，5 秒完整镜头，无字幕、无水印
```

审核失败同样消耗一次提交，出现该错误应先改写提示词，不要原样重试。

## 7. 状态与错误

| 含义 | 火山方舟格式 | OpenAI Video 格式 |
|---|---|---|
| 排队 | `queued` | `queued` |
| 生成中 | `running` | `in_progress` |
| 成功 | `succeeded` | `completed` |
| 失败 | `failed` | `failed` |
| 获取成片 | `content.video_url` | `GET /v1/videos/{id}/content` |

创建接口返回 200 仅代表受理成功，必须继续读取任务状态。

| 现象 | 处理 |
|---|---|
| `404 Invalid URL (GET ...)` | 请求使用了 HTTP 并被 301 降级，改用 HTTPS 重发 |
| `401` | 检查 API Key 有效性与 `Bearer ` 前缀 |
| `403` | 检查 Key 权限、可用型号、账户余额与限额 |
| `404` | 检查 ID 是否为本人创建且未过期 |
| `429` | 降低频率；素材接口每账号每分钟最多 120 次，多 Key 共用 |
| `200` 但返回 `text/html` | 请求未进入接口层，检查协议与路径 |
| `failed` 且提示 copyright restrictions | 提示词包含版权指向，按第 6 节改写 |
| `failed` 其他原因 | 读取 `error` 与 `upstream_id`，修正后重新提交 |

## 8. 使用要求

- 创建任务与真人授权会话均可能计费或占用额度，仅为实际业务需求调用，不得为验证接口反复创建付费任务；确认接口连通性应使用素材组的创建与删除，不产生计费。
- 素材须属于当前账号且状态为 `Active`，通过素材 ID 而非组 ID 拼接 `asset://` 引用。
- 普通素材入库不代替真人授权。授权须由本人完成，打开链接或创建会话不表示授权成功。
- 真人授权的 `CallbackURL` 可省略；省略时服务端在创建后 3 分钟内每 15 秒自动查询，授权人须尽快完成 H5；超时后用保存的 `BytedToken` 主动调 `GetVisualValidateResult`。需要接收通知时指定自有 HTTPS 地址。开通状态以服务方确认为准。
- 授权成功后服务端自动绑定真人组，无需再上传；用 `ListAssets` 传 `Filter.GroupIds` 与 `Filter.GroupType="LivenessFace"` 获取素材，状态 `Active` 后再用素材 ID 拼接 `asset://`。
- 不要输出或分享真实 API Key、授权 token 与带签名的媒体链接。
- 更多参数、素材引用与错误细节见 [接口、参数与示例](references/seedance-api.md)。
