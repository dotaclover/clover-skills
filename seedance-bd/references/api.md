# 百度 AI 网关接口

## 端点与鉴权

```env
BAIDU_AI_URL=https://ai-gateway.baidubce.com
BAIDU_AI_KEY=<百度 AI 网关分配的 Key>
```

所有请求使用 `Authorization: Bearer $BAIDU_AI_KEY`。这不是千帆 QF，也不是旧/新 VOD。不要把 base URL 设置成带 `/v1`、`/api/v3` 的完整接口，不要使用火山 AK/SK 签名。

以下 curl 是 Bash 示例；PowerShell 可用 `curl.exe`、`$env:BAIDU_AI_KEY` 并通过 UTF-8 JSON 文件传 `--data-binary @body.json`。真实密钥从环境取，不粘贴进共享脚本。响应可能含临时凭据或签名 URL，下面不直接打印正文。

## 视频任务

```bash
# 产生费用：只有明确获准生成后才执行
curl --silent --show-error --output /dev/null --write-out 'HTTP %{http_code}\n' \
  "$BAIDU_AI_URL/api/v3/contents/generations/tasks" \
  -H "Authorization: Bearer $BAIDU_AI_KEY" -H 'Content-Type: application/json' \
  --data '{"model":"doubao-seedance-2-0-mini-260615","content":[{"type":"text","text":"生成一个简单的5秒视频"}],"duration":5,"resolution":"720p","ratio":"16:9","generate_audio":true,"watermark":false}'

curl --silent --show-error --output /dev/null --write-out 'HTTP %{http_code}\n' \
  "$BAIDU_AI_URL/api/v3/contents/generations/tasks/$TASK_ID" \
  -H "Authorization: Bearer $BAIDU_AI_KEY"
```

提交响应含任务 `id`，查询直到 `succeeded`/`failed`/`cancelled` 等终态，以实际响应为准。`queued`/`running` 不是成片。脚本保留任务 ID 和状态，但隐藏输出媒体 URL；应用需私下读取完整响应。

核心参数：

| 参数 | 类型 | 说明 |
|---|---|---|
| `model` | string | 完整 Seedance 型号，不使用 `S2.0` 之类 QF 短名 |
| `content` | array | 文本和参考素材数组 |
| `duration` | integer | 输出秒数；5 秒为最小冒烟示例，范围以具体模型约束为准 |
| `resolution` | string | 示例 `720p`，分辨率影响费用；不要据一型号推断其他型号支持范围 |
| `ratio` | string | 示例 `16:9` |
| `generate_audio` / `watermark` | boolean | 保留显式 `false`，不要当成未提供 |

参考素材格式：

```json
{"type":"image_url","image_url":{"url":"asset://asset-EXAMPLE"},"role":"reference_image"}
{"type":"video_url","video_url":{"url":"https://example.com/input.mp4"},"role":"reference_video"}
{"type":"audio_url","audio_url":{"url":"https://example.com/input.wav"},"role":"reference_audio"}
```

首尾帧图片角色为 `first_frame`/`last_frame`；通用参考图不是 `reference`。素材组合、数量和编辑能力以模型和当前提供商实际验证为准。不能保证从火山账号拿到的 asset ID 在百度账号可用。

可接入候选完整型号（不等于本轮全型号收费成片验收）：

- `doubao-seedance-2-0-260128`
- `doubao-seedance-2-0-fast-260128`
- `doubao-seedance-2-0-mini-260615`
- `doubao-seedance-2-5-260628`

## 素材 Action

统一 `POST /?Action=<Action>&Version=2024-01-01`，JSON 字段大小写敏感，成功响应通常为 `ResponseMetadata` + `Result`。项目明确传 `ProjectName: "default"` 或当前账号真实项目。

| Action | 核心参数 |
|---|---|
| `CreateAssetGroup` | `Name`、`GroupType: "AIGC"`，可选 `Description` |
| `GetAssetGroup` | `Id` |
| `ListAssetGroups` | `Filter.GroupType` 为 `AIGC` 或 `LivenessFace`，分页 `PageNumber`/`PageSize` |
| `UpdateAssetGroup` | `Id`，以及 `Name` / `Description` |
| `DeleteAssetGroup` | `Id`，不可逆；不可用它假装撤回肖像授权 |
| `CreateAsset` | `GroupId`、`Name`、`AssetType`（`Image`/`Video`/`Audio`）、`URL` |
| `GetAsset` | `Id` |
| `ListAssets` | `Filter.GroupType`；按组筛选另传 `Filter.GroupIds: ["group-..."]` |
| `UpdateAsset` | `Id`，可选修改 `Name` 等当前接口支持字段 |
| `DeleteAsset` | `Id`，不可逆；删文件不等于撤回肖像授权 |
| `ListAuthorizedFirstAssetByGroups` | `GroupIds`、`Statuses: ["Active","Processing"]`；只查询已知已授权组，不从普通空列表推断资产不存在 |

```bash
curl --silent --show-error --output /dev/null --write-out 'HTTP %{http_code}\n' \
  "$BAIDU_AI_URL/?Action=ListAssets&Version=2024-01-01" \
  -H "Authorization: Bearer $BAIDU_AI_KEY" -H 'Content-Type: application/json' \
  --data '{"ProjectName":"default","Filter":{"GroupType":"LivenessFace"},"PageNumber":1,"PageSize":10}'
```

素材上传 URL 必须能被上游访问。普通 AIGC 素材入库后，先查到 `Active` 才尝试 `asset://` 生成引用；`Processing` 不是完成。不要将普通 `CreateAssetGroup` 当真人认证接口。

## 真人 H5

```bash
curl --silent --show-error --output /dev/null --write-out 'HTTP %{http_code}\n' \
  "$BAIDU_AI_URL/?Action=CreateVisualValidateSession&Version=2024-01-01" \
  -H "Authorization: Bearer $BAIDU_AI_KEY" -H 'Content-Type: application/json' \
  --data '{"ProjectName":"default","CallbackURL":"https://example.com/seedance/callback"}'

# BYTED_TOKEN 应由私有应用保管；不要直接在共享终端打印请求/响应
curl --silent --show-error --output /dev/null --write-out 'HTTP %{http_code}\n' \
  "$BAIDU_AI_URL/?Action=GetVisualValidateResult&Version=2024-01-01" \
  -H "Authorization: Bearer $BAIDU_AI_KEY" -H 'Content-Type: application/json' \
  --data "{\"ProjectName\":\"default\",\"BytedToken\":\"$BYTED_TOKEN\"}"
```

创建结果为 `Result.BytedToken`、`Result.H5Link`；由真人自行打开并完成同意，随后查询 `GetVisualValidateResult` 得 `Result.GroupId`。测试不代替真人扫码。

技能脚本默认会遮住这两个短期凭据。确需把 H5 发给真人时，只把一次创建响应写入新的本机私有文件；文件可能包含可直接使用的 Token 和链接，不得加入 Git 或共享日志：

```powershell
python scripts/seedance.py --env-file C:/private/.env `
  --private-output C:/private/new-h5-session.json `
  h5-create --allow-write --callback-url https://example.com/seedance/callback
```

文件已存在时脚本拒绝覆盖。读取后把 `BytedToken` 放入进程环境 `BAIDU_SEEDANCE_BYTED_TOKEN` 再执行 `h5-result`；不要把 Token 写进命令参数。

`CallbackURL` 按官方 H5 契约是用户认证完成后跳转的浏览器 GET 地址，不能不经验证承诺百度会发送服务端异步 POST 状态通知。结果以当前账号真实查询为准；可使用受控轮询兜底，但不把 404 擅自转为 Pending。不要承诺 `authorization.valid_days`、自定义1天授权或主动撤回 API 已支持。

## 错误判断

- 401/403：记录具体错误代码，检查百度网关 Key、账号开通和权限，不更换为火山 AK。
- H5 `404 Visual Face token not found`：真实记录失败，区分是否扫码、是否过期；不能据此声称完整真人授权闭环可用。
- `ListAssets` 缺 `Filter.GroupType` 报错：补充过滤条件，不误判凭据失效。
- 普通列表空、但控制台可见素材：普通自有素材与授权素材可能走不同查询；用已知授权 GroupIds 的 Action核对，不猜测另一个账号。
- 不打印完整上游错误对象到公开日志，其中可能带临时 URL 或凭据。保留 HTTP、错误代码、RequestId 和安全摘要。

## 来源

- 百度 AI 网关 Seedance 文档：[文档入口](http://ai-gateway.baidubce.com:8520/#3.Seedance/Seedance%E6%8E%A5%E5%8F%A3.md)。该入口是 HTTP，文档不是凭据提交端点；运行请求始终使用 HTTPS 网关。
- 火山官方协议参考：[H5创建](https://ark.volcengine.com/region:cn-beijing/docs/h5-create-visual-validate-session-api.md)、[H5结果](https://ark.volcengine.com/region:cn-beijing/docs/asset-group-id-get-visual-validate-result-api.md)、[真人流程](https://ark.volcengine.com/region:cn-beijing/docs/guide-preview.md)。这些是协议参考，不证明百度当前账号开通情况或供应商服务承诺完全相同。
