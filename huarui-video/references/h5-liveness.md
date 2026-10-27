# 华锐 H5 真人授权流程

## 创建 H5

使用华锐 Bearer Key 调用：

```http
POST https://suanli.huaruiai.com/?Action=CreateVisualValidateSession&Version=2024-01-01
Content-Type: application/json
Authorization: Bearer <华锐 API Key>
```

默认 Body：

```json
{"ProjectName":"default"}
```

只有用户提供并确认了公网 HTTPS 回调时才增加 `CallbackURL`。保存 `Result.BytedToken` 和 `Result.H5Link` 到当前私有运行上下文，不能写入 Git、共享日志或普通 REF。

## 真人完成后的核验

真人本人完成 H5 操作后，使用同一账号、同一项目和原始 Token：

```http
POST https://suanli.huaruiai.com/?Action=GetVisualValidateResult&Version=2024-01-01
Content-Type: application/json
Authorization: Bearer <华锐 API Key>
```

```json
{"ProjectName":"default","BytedToken":"<当前私有 Token>"}
```

只有同时满足以下条件才算核验成功：

- `ResultCode=10000`；
- 返回真实 `GroupId`；
- 用该 `GroupId` 查询到 `GroupType=LivenessFace`；
- 组内至少一个素材最终为 `Active`。

成功后将 Group ID、素材 ID、名称、状态、项目和检查时间写入 `references/huarui-account-assets.md`。不要用通知、浏览器成功码、自填 Group ID 或 H5 页面可打开代替主动 API 核验。

## 失败处理

- H5 创建失败：保留真实错误码和消息，不循环创建。
- `404 token not found`：按真实失败报告，不改写为等待中。
- 核验尚未完成：等待真人操作后再查，不代替真人授权。
- 组已返回但 Asset 仍 `Processing`：按 10 秒间隔有限轮询，超过合理超时则报告待处理，不提交视频。
