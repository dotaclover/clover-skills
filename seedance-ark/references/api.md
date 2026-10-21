# 官方接口与调用示例

## 1. 两套凭据与端点

| 用途 | 端点 | 鉴权 |
|---|---|---|
| 视频创建、查询 | `https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks` | `Authorization: Bearer $ARK_API_KEY` |
| 素材与 H5 Action API | `https://ark.cn-beijing.volcengineapi.com/?Action=<Action>&Version=2024-01-01` | AK/SK 计算 HMAC V4 |

本机 `.env` 变量名示例，值由用户自行配置，不在技能中保存真实凭据：

```dotenv
ARK_API_KEY=<方舟视频推理API-Key>
ARK_ASSET_ACCESS_KEY=<IAM-Access-Key-ID>
ARK_ASSET_SECRET_KEY=<IAM-Secret-Access-Key>
ARK_ASSET_PROJECT_NAME=default
```

API Key 在方舟 API Key 管理页取得；AK/SK 在火山引擎 IAM API 访问密钥管理页取得。IAM 素材权限、项目访问、API 真人认证权益和模型推理开通是不同检查项，不能相互替代。

脚本使用 Python 标准库。以下命令从技能目录执行；`--env-file` 为可选全局参数，放在子命令之前。PowerShell 使用 `python` 或已安装 Python 的绝对路径；cURL 示例使用 Bash 语法，PowerShell 应调用 `curl.exe` 并正确传入 JSON，不能原样照搬 Bash 换行。

```bash
python scripts/seedance.py --env-file /path/to/.env asset-action ListAssetGroups \
  --body '{"ProjectName":"default"}'
```

输出默认脱敏；不要为了排查把原始响应、Authorization、H5Link、BytedToken 或素材签名 URL 写入共享日志。

## 2. 视频创建与查询

### 模型标识

以下为待按账号开通情况逐项核验的型号，不是本凭据已生成成功的承诺；本轮实测结果见 [verification.md](verification.md)。

- `doubao-seedance-2-0-260128`
- `doubao-seedance-2-0-fast-260128`
- `doubao-seedance-2-0-mini-260615`
- `doubao-seedance-2-5-260628`

不同模型的时长、分辨率和编辑参数不可简单互抄。首次成本基线使用 mini、5 秒、480p；该请求仍可能按账号和服务规则计费，用户同意后才执行。

### 最小文生视频

```bash
curl --request POST \
  'https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks' \
  --header "Authorization: Bearer ${ARK_API_KEY}" \
  --header 'Content-Type: application/json' \
  --data '{
    "model": "doubao-seedance-2-0-mini-260615",
    "content": [{"type":"text","text":"微风吹过绿色山坡，镜头缓缓向前，手绘动画质感"}],
    "duration": 5,
    "resolution": "480p",
    "ratio": "16:9",
    "generate_audio": false,
    "watermark": true
  }'
```

官方请求在顶层使用 `content`、数值型 `duration`、`resolution`、`ratio`；不是 `prompt` / 字符串 `seconds` / `metadata.content` 的其他网关包装格式。

脚本创建并查询：

```bash
python scripts/seedance.py --env-file /path/to/.env video-create \
  --allow-charge \
  --model doubao-seedance-2-0-mini-260615 \
  --prompt '微风吹过绿色山坡，镜头缓缓向前，手绘动画质感' \
  --duration 5 --resolution 480p

python scripts/seedance.py --env-file /path/to/.env video-get '<返回的任务ID>'
```

```bash
curl --request GET \
  "https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks/${TASK_ID}" \
  --header "Authorization: Bearer ${ARK_API_KEY}"
```

创建通常返回 `id`。查询状态包括 `queued`、`running`、`succeeded`、`failed`、`expired`、`cancelled`；只有 `succeeded` 且存在输出视频，才能报告生成成功。异步失败读取 `error.code` / `error.message`。查询范围及产物 URL 有期限，不能把 URL 当永久存储。

### 引用素材与角色

把以下对象放入视频请求的 `content`，与文本对象并列。`asset://` 写在媒体 `url`，不能只写进提示词。

```json
{
  "type": "image_url",
  "image_url": {"url": "asset://<已授权图片素材ID>"},
  "role": "reference_image"
}
```

| 目的 | type | role |
|---|---|---|
| 图片参考 | `image_url` | `reference_image` |
| 首帧 / 尾帧 | `image_url` | `first_frame` / `last_frame` |
| 视频参考 | `video_url` | `reference_video` |
| 音频参考 | `audio_url` | `reference_audio` |

不要把图片、视频、音频的 role 统一改成 `reference`。首尾帧模式与全模态参考模式不可混用。Seedance 2.0 系列不能只输入音频参考；需搭配图片或视频。`asset://` 必须与推理账号、项目及有效授权匹配；能列出素材不等于已经验证该素材能生成视频。

## 3. 官方素材 Action API

所有下列 Action 都使用 POST、`Version=2024-01-01` 和 HMAC V4：Region `cn-beijing`、Service `ark`。使用技能脚本计算签名，不给出把 AK 当 Bearer 的伪 cURL。控制台 BFF 的 `/api/2024-10-01/...` 与此 OpenAPI 不同，不能直接互换域名或版本。

### 已知授权组查询

```bash
python scripts/seedance.py --env-file /path/to/.env \
  asset-action ListAuthorizedFirstAssetByGroups \
  --body '{
    "GroupIds":["<已知授权组ID-1>","<已知授权组ID-2>"],
    "Statuses":["Active","Processing"],
    "ProjectName":"default"
  }'
```

`Result.Items` 是以 GroupId 为键的对象；每组返回首个符合条件的素材，含 `Id`、`GroupId`、`AssetType`、`Status`、`ProjectName`、`URL` 等。它不负责自动发现所有已授权组，也不能代替组内完整素材列表。本 Action 在当前真实账号查询成功，但尚未查到其独立公开接口文档；应保留兼容性边界。

普通管理查询仍可用于适用的库存：

```bash
python scripts/seedance.py --env-file /path/to/.env asset-action ListAssets \
  --body '{"Filter":{"GroupType":"LivenessFace"},"ProjectName":"default"}'
```

`ListAssets` 的 `Filter.GroupType` 必须按资源类型填写。不要建议省略整个 Filter 的“裸查询”；已实测会报缺参数。普通查询为空或 `GetAsset` 404，不等于已接收授权的控制台素材不存在。

### H5 真人认证

用户同意创建测试会话后：

```bash
python scripts/seedance.py --env-file /path/to/.env \
  asset-action CreateVisualValidateSession --allow-write \
  --body '{
    "CallbackURL":"https://your-domain.example/face/callback",
    "ProjectName":"default"
  }'
```

官方公开的请求字段只有：

| 字段 | 要求 |
|---|---|
| `CallbackURL` | 必填，认证完成后浏览器跳转到的可访问地址 |
| `ProjectName` | 默认 `default`，大小写敏感 |

响应为 `Result.BytedToken`、`Result.H5Link`、`Result.CallbackURL`。Token 自生成起有效 30 分钟，仅支持认证一次；H5 链接及 Token 不公开、不进 Git。脚本默认隐藏敏感响应，不为排查而打开全量原文日志。

确需把 H5 发给真人时，只把这一次响应写到新的本机私有文件。文件含可直接使用的短期凭据，不能加入 Git 或共享日志：

```powershell
python scripts/seedance.py --env-file C:/private/.env `
  --private-output C:/private/new-ark-h5-session.json `
  asset-action CreateVisualValidateSession --allow-write `
  --body '{"CallbackURL":"https://your-domain.example/face/callback","ProjectName":"default"}'
```

文件已存在时脚本拒绝覆盖。读取后将 `BytedToken` 放入当前进程环境 `ARK_BYTED_TOKEN`，再做服务端结果核验：

```powershell
python scripts/seedance.py --env-file C:/private/.env `
  asset-action GetVisualValidateResult --body '{"ProjectName":"default"}'
```

真人本人完成认证后，服务端调用：

```http
POST /?Action=GetVisualValidateResult&Version=2024-01-01
Host: ark.cn-beijing.volcengineapi.com
Content-Type: application/json
Authorization: <服务端实际计算的HMAC签名>
```

```json
{
  "BytedToken": "<服务端短期保存的本次凭证>",
  "ProjectName": "default"
}
```

成功结果只保证有 `Result.GroupId`，不能强制要求官方未列出的 `ResultCode` 或 `ExpireTime`。回跳查询串的 `resultCode=10000` 可作交互提示，不能代替服务端核验。`CallbackURL` 是点击“完成”后的浏览器 GET 回跳，不是已证实的服务端 POST 事件投递。

当前官方账号创建 H5 返回 `SubscriptionRequired`，见 [实测](verification.md)。收到此错误应停止重复创建，核对本项目对应权益/开通条件；不要为了“试通”更换成百度后宣称官方已成功，也不要代替用户购买或订阅。

### 创建、查询、删除素材

| Action | 请求核心字段 | 注意事项 |
|---|---|---|
| `CreateAssetGroup` | `Name`、`Description`（可选）、`GroupType: AIGC`、`ProjectName` | 公开接口当前仅支持创建 AIGC，不是创建真人组的替代方式 |
| `CreateAsset` | 按官方最新 schema 指定 `GroupId`、`Name`、`AssetType`、`URL`、`ProjectName` | `URL` 大写；素材进入处理后仍须查到 Active，不等于上传即获真人授权 |
| `GetAsset` | `Id`、`ProjectName` | `Id` 不是 `AssetId`；对授权使用库存可能不适用 |
| `DeleteAsset` | `Id`、`ProjectName` | 不可逆删除素材，不等于撤回肖像授权 |
| `DeleteAssetGroup` | `Id`、`ProjectName` | 不可逆批量删除组内素材；先确认资源与用户授权 |

删除及其他写操作仅对用户明确指定的资源加 `--allow-write` 执行；不能把示例改成循环删除账号所有库存。

官方删除组文档明确：**在控制台创建的真人组**，仅可删除授权过期或拒绝接收的组；有效期内、尚未开始或已接收的组不能删除。不把这段限制扩张成“所有 H5 API 真人组一定不能删”，后者尚未实测。

## 4. 授权期限：能确认与不能确认

- 控制台真人素材邀约界面可设置授权有效期。
- 公开 `CreateVisualValidateSession` 未列出 `authorization.valid_days`、开始时间、结束时间或期限枚举。
- 公开 `GetVisualValidateResult` 只列出 `GroupId`，没有保证返回肖像授权到期时间。
- 当前无期限和带期限探测都先被 `SubscriptionRequired` 拦截，不能证明期限字段支持、被忽略或会被拒绝。
- 不写“API 能设一天”“二维码固定 120 秒”“30/90/365 天枚举”“只能商务白名单”“授权永久”等未核实结论。
- 业务侧可以按合同另外控制使用期限，但这不等于上游同意了该期限，也不等于平台已经撤权；不能绕过仍有效的肖像同意范围。

## 5. 官方依据

- [创建视频任务](https://ark.volcengine.com/region:cn-beijing/docs/create-video-generation-task-api.md)
- [查询视频任务](https://ark.volcengine.com/region:cn-beijing/docs/get-video-generation-task-api.md)
- [创建 H5 认证会话](https://ark.volcengine.com/region:cn-beijing/docs/h5-create-visual-validate-session-api.md)
- [获取真人 Asset Group ID](https://ark.volcengine.com/region:cn-beijing/docs/asset-group-id-get-visual-validate-result-api.md)
- [真人素材 API 使用指南](https://ark.volcengine.com/region:cn-beijing/docs/guide-preview.md)
- [创建素材组](https://ark.volcengine.com/region:cn-beijing/docs/create-asset-group-api.md)
- [删除素材组](https://ark.volcengine.com/region:cn-beijing/docs/delete-asset-group-api.md)
- [控制台上传真人素材](https://ark.volcengine.com/region:cn-beijing/docs/upload-real-person-portrait-assets.md)
- [高级创作权益](https://ark.volcengine.com/region:cn-beijing/docs/seedance-2-0-purchase-guide.md)

按官方最新正文复核字段，不把控制台 BFF、推理接口、OpenAPI 或第三方整理的请求拼接成一套协议。
