# 连通性与资产同步流程

## 官方 Ark 检查

1. 只检查变量是否存在和非空，不输出值；缺任意一项就标记 `official_configured=false`。
2. 用 `ARK_KEY` 调用官方视频 `GET /api/v3/models`。HTTP 200 且 JSON 说明视频接口可用；401/403/网络错误必须停止官方生成路径。
3. 使用 REF 中已知组 ID，或使用用户刚提供的网页资产组结果，调用 `ListAuthorizedFirstAssetByGroups`，Version 固定 `2024-01-01`，只接受 `Active` 资源。
4. 网页侧的 `ListActiveAuthorizationAssetGroup`（`Version=2024-10-01`）在本次原始 HMAC 直连中返回 `InvalidActionOrVersion`，因此只能作为网页发现结果来源，不能直接当作公开 Ark Action 调用。
5. 同步 `references/ark-account-assets.md` 和主 SKILL 索引。删除已明确失效的旧资产记录；遇到查询失败不要清空旧记录，标记为待复核。

官方同步不是收费视频生成，不得为了连通性创建测试组或提交视频。

## 华锐检查

1. 使用固定 HTTPS Base URL 和内置 Key 调用 `GET /v1/models`。HTTP 200 且 JSON 说明视频 API 可达。
2. 调用素材 `ListAssetGroups`，筛选 `LivenessFace`；对每个返回组调用 `ListAssets`，必要时按单个 `GroupId` 查询。
3. 对所有登记的 Asset ID 调用 `GetAsset` 或等价只读查询，检查 `Status=Active`、`ProjectName` 和当前账号归属。
4. 只有模型接口、素材组列表、素材列表和逐个 Asset 检查都成功，且所有选定资产为 `Active`，才报告“华锐素材接口全部可用”。
5. 将本次检查时间、HTTP、RequestId、组/资产脱敏摘要和状态写入 `references/huarui-account-assets.md`；不写 URL、签名 URL、Key 或 Token。

## 停止条件

- 认证失败、返回 HTML、域名/协议错误、JSON 结构不符合预期：停止该 provider，不自动切换。
- `ListAssetGroups` 空不等于没有真人授权；必须结合已知组或 H5 核验结果判断。
- `Processing` 不等于可用；`Authorized` 组也不等于组内已经有 `Active` Asset。
