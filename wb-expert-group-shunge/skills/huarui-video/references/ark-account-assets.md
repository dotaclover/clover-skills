# 官方Ark账号资源核验

本文件只保留通用方法，不携带真人名称、固定Group ID或Asset ID。当前资源清单存仓库外私有任务目录，由授权账号重新查询；历史成功不证明当前库存或授权仍有效。

## 已知协议经验

历史中性案例（不是当前已验证）：模型检查HTTP200；网页ListActiveAuthorizationAssetGroup / Version=2024-10-01直调公开HMAC曾返回404 InvalidActionOrVersion；在授权人提供本人组ID后，ListAuthorizedFirstAssetByGroups / Version=2024-01-01曾返回Active素材。案例仅说明接口差异，不推断任何当前账号库存、订阅或可用性。

视频Bearer与素材IAM HMAC独立，STS需Session Token；变量名按provider-config.md及seedance-dev。官方素材域名 `https://ark.cn-beijing.volcengineapi.com/`，项目由当前用户配置。

## 私有记录字段

provider、账号配置来源（不含值）、项目、查询时间、Action/Version、request_id、Group ID、Asset ID、状态、授权有效期及依据。只存实际返回，不从组ID猜素材；错误保留原值标未验证。

引用使用 `asset://<实际Asset ID>`，不使用Group ID。提示词image 1/image 2与content数组顺序一致。Active、本人同意、授权未过期、当前项目可用分别核验。Key、AK/SK、Token、H5链接与签名URL不进入共享文档。官方任务由迟空负责，华锐资源不能跨用。
