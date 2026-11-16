# 华锐私有资产登记方法

不在共享技能记录真人名称、固定组和素材ID。只在用户授权的仓库外私有任务目录登记当前华锐账号、项目与授权关系；不得跨用官方Ark库存。

## 私有登记字段

检查时间、provider、账号配置来源、ProjectName、Group ID、Asset ID、状态、本人授权依据/有效期、H5核验ResultCode、request_id。只写接口真实返回；BytedToken、H5Link和签名URL仅在受控私有运行上下文保存，不进Git或共享日志。

H5成功须ResultCode=10000、真实GroupId及LivenessFace组内Active素材。Group ID不是Asset ID；Processing、网页回跳和通知不是生成可用证据。失败保留旧记录标待复核，不自动删除。

## 历史限制

历史中性案例（不是当前已验证）：模型接口HTTP200但素材ListAssetGroups返回502 UpstreamError，消息为official Ark asset channel requires administrator AK/SK configuration。它说明视频Key可用不证明素材/H5已开通，不代表任何当前账号状态。按选定账号和项目只读复核。
