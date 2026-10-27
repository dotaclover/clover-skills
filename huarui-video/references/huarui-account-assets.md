# 华锐账号资产登记

本 REF 只记录华锐接口侧的账号、组和 Asset 状态，不代表官方 Ark 资产库存。每次连通性检查、H5 核验或生成前同步时更新。

## 当前已知资产

这些 Asset ID 曾在华锐视频任务中实际使用成功，但仍需每次通过华锐只读素材接口复核状态：

| 名称 | Asset ID | 来源/组 | 当前状态 | 最后核验 |
|---|---|---|---|---|
| 林冯（组 95tcv） | `asset-20261013113659-4jz89` | `group-20261013113356-95tcv` | 待华锐复核 | 2026-10-27 |
| 缪志翔 | `asset-20261013113532-s2q8c` | `group-20261013113402-czjwb` | 待华锐复核 | 2026-10-27 |
| 林冯（组 lp5rb） | `asset-20261013114040-jspbc` | `group-20261013113838-lp5rb` | 待华锐复核 | 2026-10-27 |
| 林冯1 | `asset-20261013114340-2gqft` | `group-20261013114221-99qv2` | 待华锐复核 | 2026-10-27 |

## H5 核验新增资源

| 核验时间 | Group ID | Asset ID | 名称 | 状态 | ProjectName | ResultCode |
|---|---|---|---|---|---|---|
| 暂无 | — | — | — | — | — | — |

只写接口真实返回值。BytedToken、H5Link、媒体 URL、签名 URL、API Key 和 AK/SK 永不写入本 REF。


## 2026-10-27 只读检查

- 华锐视频模型接口：HTTP `200`，视频 API 可连通。
- 华锐 `ListAssetGroups`（`Filter.GroupType=LivenessFace`）：HTTP `502`。
- RequestId：`202610270609422580522928268d9d6e9ogxWLX`。
- 上游错误：`UpstreamError`，消息为 `official Ark asset channel requires administrator AK/SK configuration`。
- 结论：当前不能报告华锐素材接口全部可用；华锐视频 Key 有效不等于华锐素材通道已配置。H5 创建和真人核验也应在素材通道修复前单独报告实际结果，不能把视频接口成功当作 H5/素材能力已开通。
