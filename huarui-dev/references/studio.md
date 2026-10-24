# Seedance 工作台内部调用链

## 页面与接口

- `/video/seedance`：视频创作。
- `/video/seedance/tasks`：任务列表。
- `/video/seedance/models`：模特/真人授权相关页面入口。
- `GET /api/studio/seedance/models`：返回当前用户分组可用模型。
- `POST /pg/studio/seedance/generations`：登录用户提交生成任务。
- `GET /api/studio/seedance/tasks`：读取当前用户任务。
- `POST /api/studio/uploads`：上传供上游读取的临时素材。
- `GET/HEAD /uploads/studio/<user>/<name>`：临时素材读取，默认保留 72 小时。

## 调用链

```text
浏览器登录会话
  -> 工作台参数校验与素材规范化
  -> 官方 doubao 任务插件
  -> 模型/渠道分发
  -> 任务持久化、后台轮询、预扣与完成结算
  -> artifacts / content 成片访问
```

网页使用系统登录凭据和官方 Playground 资金来源，不读取、创建或借用用户 API Token。上游 Key 只存在服务端渠道配置中。

## 当前已实现范围

- 2.0/2.5 模型选择、时长/分辨率/比例校验。
- 图片、视频、音频参考；首帧/尾帧与普通参考素材互斥。
- 任务提交时锁定表单；成功清空输入，失败保留输入。
- 任务列表、状态读取、制品播放/下载入口。
- 本地临时素材上传、随机文件名、文件头校验、72 小时清理。
- 模特/真人授权会话、资源归属、过期会话清理及 API/网页库存隔离。

## 仍需验收

- 公网 HTTPS 回跳和真实手机/H5 同意。
- 授权成功后的资源绑定、Active 素材创建、本人素材生成成片。
- 真实百度 AI Gateway/火山渠道的完整生成、失败、退款和最终扣费对账。
- 发布环境反向代理对 `/api/studio/`、`/pg/studio/`、`/uploads/studio/` 的完整转发。
- 多节点共享上传目录、运行中的二进制/前端 hash 与源码一致性。

本文件只做内部开发导航；没有执行新的收费请求或部署操作。
