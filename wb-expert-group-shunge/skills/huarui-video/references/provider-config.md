# Provider、API地址与凭据

仅从当前任务明确授权的环境变量或仓库外私有配置获取凭据。本包不内置Key，不回显变量值，不从历史资料复制客户凭据。曾随导入资料携带的明文凭据应由持有人立即撤销/轮换；从文档删除不代表已撤销。

## 华锐

固定可信服务根 `https://suanli.huaruiai.com`，凭据 `HUARUI_API_KEY`。缺失时请用户在本地安全配置，不索取聊天明文。更换地址需明确确认接收权限，不跟随重定向转发认证。

| 用途 | 路径 | 鉴权 |
|---|---|---|
| 模型只读检查 | `/v1/models` | Bearer HUARUI_API_KEY |
| 视频提交 | `/api/v3/contents/generations/tasks` | 同上 |
| 视频查询 | `/api/v3/contents/generations/tasks/{task_id}` | 同上 |
| 素材与H5 | `/?Action={Action}&Version=2024-01-01` | 同上 |

只在授权账号/项目内查询；模型可见不代表生成已测试，H5/素材写动作和生成另行确认。

## 官方Ark兼容资料

本技能保留协议差异供核对，官方业务转迟空并读取 `seedance-dev` 官方参考，不自动跨渠道执行。

- 视频根 `https://ark.cn-beijing.volces.com/api/v3`，标准变量 `ARK_API_KEY`；旧资料 `ARK_KEY` 仅在用户明确映射时使用，不静默猜别名。
- 素材根 `https://ark.cn-beijing.volcengineapi.com/`，`ARK_ASSET_ACCESS_KEY` / `ARK_ASSET_SECRET_KEY` 用HMAC V4；旧 `ARK_ACCESS_KEY` / `ARK_SECRET_KEY` 同样需明确映射。STS另带Session Token。
- 项目 `ARK_ASSET_PROJECT_NAME`，按账号配置确认。视频Key不能代替素材AK/SK。
- `ListAuthorizedFirstAssetByGroups` 使用Version=2024-01-01；网页 `ListActiveAuthorizationAssetGroup` Version=2024-10-01不是公开HMAC Action的保证。

## 生成参数

提交前确认完整模型ID、提示词、参考素材及权限、时长、比例、分辨率、声音、水印、价格依据和预算。型号与参数范围以当前服务文档及账号证据为准；不固定5秒、720p、有声、无水印或两种比例，不跳过最终确认。

Ark兼容请求顶层content、整数duration；OpenAI Video格式另按对应文档，二选一，不创建两个任务。
