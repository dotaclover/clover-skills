# Provider、API 地址与凭据

本 REF 是 `huarui-video` 的唯一接口配置说明。官方 Ark 和华锐必须严格隔离。

## 官方 Ark

| 用途 | 地址 | 鉴权 |
|---|---|---|
| 视频连通性、模型检查 | `https://ark.cn-beijing.volces.com/api/v3/models` | `Authorization: Bearer $ARK_KEY` |
| 视频提交 | `https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks` | `Authorization: Bearer $ARK_KEY` |
| 视频查询 | `https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks/{task_id}` | `Authorization: Bearer $ARK_KEY` |
| 网页授权组发现 | 网页返回的 `ListActiveAuthorizationAssetGroup` / `Version=2024-10-01` | 作为用户提供的发现结果；当前公开 HMAC Action 不保证支持 |
| 资产查询 | `https://ark.cn-beijing.volcengineapi.com/?Action=ListAuthorizedFirstAssetByGroups&Version=2024-01-01` | HMAC V4，`ARK_ACCESS_KEY` + `ARK_SECRET_KEY` |

必须同时存在：

```text
ARK_KEY
ARK_ACCESS_KEY
ARK_SECRET_KEY
```

项目默认 `ARK_ASSET_PROJECT_NAME=default`。临时 STS 凭据还必须带 Session Token。`ARK_KEY` 不能用于 HMAC；AK/SK 不能拼成 Bearer。官方原始素材同步使用已知或用户提供的 Group ID 调用 `ListAuthorizedFirstAssetByGroups`。

## 华锐

| 用途 | 地址 | 鉴权 |
|---|---|---|
| 模型/连通性检查 | `https://suanli.huaruiai.com/v1/models` | `Authorization: Bearer <华锐 Key>` |
| 视频提交 | `https://suanli.huaruiai.com/api/v3/contents/generations/tasks` | `Authorization: Bearer <华锐 Key>` |
| 视频查询 | `https://suanli.huaruiai.com/api/v3/contents/generations/tasks/{task_id}` | `Authorization: Bearer <华锐 Key>` |
| 素材与 H5 | `https://suanli.huaruiai.com/?Action={Action}&Version=2024-01-01` | `Authorization: Bearer <华锐 Key>` |

当前内置华锐 Key：`sk-HXDLO2RCjbFWnuCM0DpaFDK9uupws3qbGSceY4anbzut9DaK`

华锐没有设置用户环境变量时，直接读取上述内置 Key；如果未来改为私有配置，优先使用 `HUARUI_API_KEY`，但不能把它发给官方 Ark。固定 Base URL 为 `https://suanli.huaruiai.com`，只使用 HTTPS。

## 统一请求默认值

- 模型：必须在提交前确认完整 ID；当前候选为 `doubao-seedance-2-0-260128`、`doubao-seedance-2-0-fast-260128`、`doubao-seedance-2-0-mini-260615` 和 `doubao-seedance-2-5-260628`，实际权限以所选 provider 的模型检查结果为准。
- 时长：默认 5 秒，实际范围以模型返回能力为准。
- 比例：只允许 `9:16`、`16:9`。
- 分辨率：默认 `720p`。
- 声音：默认 `generate_audio=true`。
- 水印：默认 `watermark=false`。
- 视频格式：统一使用 `POST /api/v3/contents/generations/tasks` 的顶层 `content`、整数 `duration` 和顶层输出参数。
