# 连通性与资产核验

只在当前任务授权内检查选定provider，不自动跨账号或跨服务同步。

## 华锐

1. 检查HUARUI_API_KEY存在性，不输出值。按provider-config.md可信HTTPS地址只读GET /v1/models。
2. HTTP200且JSON仅证明模型目录可达，不证明视频生成成功或所有能力支持。
3. 需要素材时才查询指定账号项目的LivenessFace组及选定素材，核Group ID与Asset ID不同、状态Active、当前授权关系与有效期。
4. 私有记录保存在仓库外，按provider/账号/项目隔离；仅更新真实查询结果。失败保留旧值并标待复核，不自动删除，不写共享SKILL或Git。
5. 报告检查时间、HTTP、RequestId、选定资源脱敏状态与未验证项。不输出Key、Token、H5链接、签名媒体URL或完整私人库存。

## 官方差异

官方任务交迟空使用seedance-dev与官方参考。视频Bearer与素材HMAC分离；网页ListActiveAuthorizationAssetGroup并不保证公开HMAC支持，不能用InvalidActionOrVersion判断全部素材能力不可用。仅依据用户提供且有权访问的组查询ListAuthorizedFirstAssetByGroups。

## 停止条件

认证失败、HTML响应、域名协议错误或结构不符合预期：停止该provider，不切换或收费探活。空列表不证明没有授权；Processing不是Active，Authorized组不代表素材可用于生成。不能为连通性创建删除测试组、H5会话或视频，写入与费用需另行确认。
