# 百度 AI Gateway 与 Seedance 记录

## 已核实的接入边界

- AI Gateway 地址：`https://ai-gateway.baidubce.com`。
- Ark 兼容视频创建：`POST /api/v3/contents/generations/tasks`。
- Ark 兼容视频查询：`GET /api/v3/contents/generations/tasks/<task_id>`。
- 项目使用统一 `doubao` 任务插件处理 Seedance，AI Gateway 不走千帆 FireSeries 路径。
- 百度 Key 只应存在 CloverAPI 服务端渠道配置；浏览器工作台不接触百度 Key。

## 模型记录

历史资料中出现过：

- Seedance：`doubao-seedance-2-0-260128`、`doubao-seedance-2-0-fast-260128`、`doubao-seedance-2-0-mini-260615`、`doubao-seedance-2-5-260628`。
- 文本模型：`glm-5.3`、`kimi-k3`、多个 `deepseek-*` 名称。

这些名称不等于当前账号全部可用。实际维护需同时检查渠道类型、Base URL、Key 权限、公开模型、用户分组、Token 限制和真实请求结果。`deepsek` 是用户口语写法，不能直接当作正式模型 ID。

## 重要区别

- AI Gateway：Ark 原生内容生成协议，使用完整 Seedance 模型名。
- 千帆：FireSeries 任务协议，使用 `S2.0` 等上游短名称映射。
- 华锐兼容接口：另有其自身协议和凭据边界，不能只替换域名复用百度文档。

本文件记录的是 `cloverapi` 的内部开发事实，不执行新的上游请求，也不保存真实 Key、任务 ID 或签名 URL。
