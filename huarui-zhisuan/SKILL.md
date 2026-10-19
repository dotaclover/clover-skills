---
name: huarui-zhisuan
description: 调用华锐智算的 Seedance 视频与素材 API，提供接口端点、API Key 鉴权、支持型号、请求参数、curl 示例和错误处理。适用于文生视频、参考素材生成、任务查询下载及账号私有素材管理。
agent_created: true
---

# 华锐智算 Seedance API

服务地址：`http://suanli.huaruiai.com`

所有接口使用华锐智算分配的 API Key：

```http
Authorization: Bearer <你的 API Key>
Content-Type: application/json
```

## 支持型号

| 型号 | model |
|---|---|
| Seedance 2.0（默认） | `doubao-seedance-2-0-260128` |
| Seedance 2.0 Fast | `doubao-seedance-2-0-fast-260128` |
| Seedance 2.0 Mini | `doubao-seedance-2-0-mini-260615` |
| Seedance 2.5 | `doubao-seedance-2-5-260628` |

具体可用型号以当前 Key 的权限为准，可通过 `GET /v1/models` 查询。

## 功能与端点

| 功能 | 方法与路径 |
|---|---|
| 火山方舟格式创建视频 | `POST /api/v3/contents/generations/tasks` |
| 火山方舟格式查询视频 | `GET /api/v3/contents/generations/tasks/{id}` |
| OpenAI Video 格式创建视频 | `POST /v1/videos` |
| OpenAI Video 格式查询视频 | `GET /v1/videos/{id}` |
| 下载视频 | `GET /v1/videos/{id}/content` |
| 创建、查询、列出、更新和删除素材组/素材 | `POST /?Action={Action}&Version=2024-01-01` |

视频可使用文字、图片、视频或音频参考；支持的组合以所选型号为准。素材按账号隔离，可通过 `asset://` 引用本人素材。

## 快速调用

以下为 Bash 示例；把 Key 放入当前进程环境，不写入共享脚本：

```bash
export HUARUI_BASE_URL='http://suanli.huaruiai.com'
read -rsp 'API Key: ' HUARUI_API_KEY; echo
export HUARUI_API_KEY

curl --silent --show-error --fail-with-body \
  "$HUARUI_BASE_URL/api/v3/contents/generations/tasks" \
  -H "Authorization: Bearer $HUARUI_API_KEY" \
  -H 'Content-Type: application/json' \
  --data '{"model":"doubao-seedance-2-0-260128","content":[{"type":"text","text":"生成一个5秒的科技感城市宣传视频"}],"duration":5,"resolution":"720p","ratio":"16:9"}'
```

保存返回的 `id`，通过查询接口等待成功后下载。默认示例采用 Seedance 2.0、5 秒、720p、16:9。

## 参数与素材调用

使用前阅读 [接口、参数与 curl 示例](references/seedance-api.md)：

- 第 1 节：地址、API Key 和型号。
- 第 2–4 节：两种视频请求格式、参数、查询状态和下载。
- 第 5 节：图片/视频/音频角色与首尾帧。
- 第 6 节：素材组、素材、`asset://` 和可选真人授权接口。
- 第 7 节：错误处理与调用注意事项。

## 注意事项

- 两种视频格式任选一种创建，同一视频不要重复提交；创建操作可能计费。
- 使用返回的真实任务/素材 ID；示例占位 ID 不可直接调用。
- 素材须属于当前账号且为 `Active`；不同账号不能互访或引用对方素材。
- 普通素材入库不代替真人授权；真人授权接口的开通范围请向服务方确认。
- 当前地址为 HTTP，不提供 TLS 传输加密；敏感生产业务请先联系服务方确认 HTTPS 地址。
- 仅在用户要求生成或创建素材时执行相应写操作；不得为检查接口而重复创建付费任务。不要输出或分享真实 Key、授权 token 和带签名的媒体链接。
