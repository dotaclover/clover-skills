# 服务端素材接口实测记录

本文件只保存脱敏结果，不记录 API Key、认证会话令牌、H5 链接、签名素材 URL 或私人照片。

## 2026-10-22：素材 URL 作为 Seedance 参考输入

环境：经 `https://juhe.top` 使用测试凭据调用。真实付费测试模型为 `doubao-seedance-2-0-mini-260615`。

| 输入 | 结果 |
| --- | --- |
| 素材查询返回的 `result.URL` 作为 `reference_image` | 任务成功完成 |
| 素材查询返回的 `result.URL` 作为 `reference_video` | 任务成功完成 |

结论：素材查询返回的 `result.URL` 可以直接作为 Seedance 的 `reference_image` / `reference_video` 输入，不需要先转存。该 URL 仍受有效期、源站可访问性和素材 `Active` 状态约束，网关不会为 URL 引用自动重查状态。

## 2026-10-22：素材接口路由与参数契约

环境：经 `https://juhe.top` 聚合入口，使用本机安全存储的测试凭据，请求体显式 UTF-8。全部为免费读写探测。

| 探测 | HTTP | 可核实结果 |
| --- | ---: | --- |
| 分组列表 POST 到列表子路径 `.../list` | 200 | `code: 0`，返回 `Items` 与 `TotalCount` |
| 分组列表不带 `Filter.GroupType` | 400 | `invalid_parameter`：`Filter.GroupType is required` |
| 素材列表 POST 到 `.../list` | 200 | `code: 0`，返回素材 `Items`（含 `Status`、`URL`） |
| 素材列表不带过滤条件 | 200 | 列出账户内全部素材 |
| 素材列表带 `Filter.GroupType` | 400 | `invalid_parameter`：素材列表不支持该字段 |
| 分组、素材取单个 GET `?id=` | 200 | 返回对应记录 |
| 素材删除：ID 放查询串 `?id=` | 404 或成功 | 参数位置正确；不存在 ID 返回 `material_not_found` |
| 分组删除：请求体 `{"Id": ...}` | 404 或成功 | 参数位置正确；不存在 ID 返回 `material_not_found` |

结论：

- 分组列表必须带 `Filter.GroupType`；素材列表不接受 `Filter.GroupType`，只按 `GroupIds`、`Statuses` 和分页参数过滤。
- 素材 ID 放查询串，分组 ID 放请求体；CLI 已封装这两套位置。
- 列表与单条查询只返回当前用户、当前站点拥有且所属账户仍可用的资源。

## 2026-10-22：asset:// 引用链路

代码核查与接口契约确认：

- `asset://<素材ID>` 由聚合 API 校验素材归属、类型、`Active` 状态、所属分组和服务账户。
- 校验通过后，网关把公共素材 ID 改写成服务可识别的原生素材 URI，再将视频任务发送到对应账户。
- 该改写不依赖素材查询返回的临时预览 URL，因此不会在提交阶段用 URL 替换 `asset://` 引用。
- 账户不同返回 `material_account_mismatch`；素材未完成处理返回 `material_not_active`；类型不符返回 `material_type_mismatch`。

## 2026-10-22：真人认证链路

环境：经 `https://juhe.top`，使用测试凭据完成免费路由与会话探测。H5 链接内容未落盘。

| 探测 | HTTP | 结果 |
| --- | ---: | --- |
| 创建真人认证会话 | 200 | 返回认证组 ID 与 H5 授权链接；链接仅记录存在性，不记录内容 |
| 查询认证结果 | 200 | `Status: running`（尚无真人完成认证） |
| 查询不存在的认证组 | 404 | `material_not_found` |
| 未完成认证时向真人组上传素材 | 409 | `material_group_not_verified` |
| 普通分组直接指定 `GroupType: LivenessFace` | 400 | 必须通过真人认证会话创建 |

结论：聚合入口已接通真人认证会话创建、结果轮询和认证后素材上传。认证必须由真实自然人本人在 H5 页面完成，程序侧不能代办；状态从 `running` 变为 `completed` 后才允许创建真人素材。H5 授权链接属敏感物，不落盘、不写日志，只转发给完成认证的本人。
