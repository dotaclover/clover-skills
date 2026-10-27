# 官方 Ark 账号资源说明

本 REF 专门说明 `huarui-video` 使用的火山方舟官方账号资源。它不是华锐网关的通用素材列表；资源必须属于当前官方账号、项目和授权关系，不能跨账号或跨渠道复用。

## 当前账号资源

2026-10-27（北京时间）使用网页返回的 `ListActiveAuthorizationAssetGroup` 结果取得 4 个 `LivenessFace` 授权组，再用官方素材 Action `ListAuthorizedFirstAssetByGroups` 查询每组首个可用资源。

查询请求：

- 官方素材域名：`https://ark.cn-beijing.volcengineapi.com/`
- Action：`ListAuthorizedFirstAssetByGroups`
- Version：`2024-01-01`
- ProjectName：`default`
- Statuses：`Active`、`Processing`
- HTTP：`200`
- RequestId：`20261027130223C3ED299B48DE250C7851`

| 组名 | Group ID | Asset 名称 | Asset ID | 类型 | 状态 | 有效期 |
|---|---|---|---|---|---|---|
| 林冯1 | `group-20261013114221-99qv2` | `B2AAD8E8-B684-4841-A258-C463C2B1AD9E.jpeg` | `asset-20261013114340-2gqft` | Image | Active | 2026-10-13 至 2026-11-30 |
| 林冯 | `group-20261013113838-lp5rb` | `3631da55e8e7b1c62e92e66e14ac470f.jpeg` | `asset-20261013114040-jspbc` | Image | Active | 2026-10-13 至 2026-11-30 |
| 缪志翔 | `group-20261013113402-czjwb` | `IMG_1538.jpeg` | `asset-20261013113532-s2q8c` | Image | Active | 2026-10-13 至 2026-11-30 |
| 林冯 | `group-20261013113356-95tcv` | `IMG_4625.jpeg` | `asset-20261013113659-4jz89` | Image | Active | 2026-10-13 至 2026-11-30 |

网页接口返回的 4 个组均为 `Status: Authorized`、`GroupType: LivenessFace`、`ProjectName: default`、`AccountType: Company`。上表的 Asset ID 是随后官方 Action 查询返回的真实 ID，不是根据组 ID 推测生成。

## 凭据与接口边界

- `ARK_KEY`：方舟视频推理 API Key，只用于视频接口的 Bearer 鉴权。
- `ARK_ACCESS_KEY` / `ARK_SECRET_KEY`：火山 IAM AK/SK，用于官方素材 Action 的 HMAC V4 鉴权。
- 临时 STS 凭据还需要对应的 Session Token；长期 AK/SK 不需要 Session Token。
- 官方视频接口和官方素材接口是两套不同端点，不能把 `ARK_KEY` 当作素材接口的 AK，也不能把华锐 Bearer Key 发到火山接口。
- 网页返回的 `Version: 2024-10-01`、`ListActiveAuthorizationAssetGroup` 用于发现当前账号的授权组；素材引用查询使用 `ListAuthorizedFirstAssetByGroups` 的 `Version: 2024-01-01`，两者不要混用。

## 视频引用

引用素材时使用 Asset ID，不使用 Group ID：

```json
{"type":"image_url","image_url":{"url":"asset://asset-20261013114340-2gqft"},"role":"reference_image"}
```

提示词中必须使用 `image 1`、`image 2` 等显式指代对应图片。使用多个素材时，`content` 数组中的图片顺序就是提示词里的编号顺序。

资源 URL、签名 URL、Token、AK/SK 和 API Key 不写入本 REF；资源状态变化或授权到期后，必须重新用官方接口查询，不能继续假设当前表格永久有效。

## 2026-10-27 原始 API 复核

- 官方 Ark 视频模型检查：HTTP `200`。
- 直接调用网页返回的 `ListActiveAuthorizationAssetGroup` / `Version=2024-10-01`：HTTP `404`，错误 `InvalidActionOrVersion`；该 Action 属于网页侧发现结果，不能作为公开 HMAC Action 直接调用。
- 使用网页已提供的 4 个 Group ID 调用 `ListAuthorizedFirstAssetByGroups` / `Version=2024-01-01`：HTTP `200`。
- RequestId：`20261027141825660A62ACD359D498893D`。
- 4 个资源仍全部为 `Image / Active / default`，Asset ID 与本 REF 现有记录一致。
