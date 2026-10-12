# new-api 中的百度 Seedance 处理

本文对应 `C:\code\cloverapi` 当前实现，写入 Skill 时不复制真实 Key。

## 1. AI 网关原生 Seedance

环境变量：

```env
BAIDU_AI_URL=https://ai-gateway.baidubce.com
BAIDU_AI_KEY=<AI 网关 Key>
```

提交任务：

```http
POST {BAIDU_AI_URL}/api/v3/contents/generations/tasks
Authorization: Bearer {BAIDU_AI_KEY}
Content-Type: application/json
```

```json
{
  "model": "doubao-seedance-2-5-260628",
  "content": [{"type": "text", "text": "生成一个简单的5秒视频"}],
  "duration": 5
}
```

查询任务：

```http
GET {BAIDU_AI_URL}/api/v3/contents/generations/tasks/{task_id}
Authorization: Bearer {BAIDU_AI_KEY}
```

当前已验证可提交的模型：

- `doubao-seedance-2-0-260128`
- `doubao-seedance-2-0-fast-260128`
- `doubao-seedance-2-0-mini-260615`
- `doubao-seedance-2-5-260628`

AI 网关返回任务 ID 后是异步任务；提交成功不等于视频已完成，必须查询到 `succeeded` 或明确失败状态。

## 2. new-api 任务插件路由

`plugins/tasks/doubao/plugin.js` 声明了：

```text
channelTypes: [54, 45, 46]
```

其中：

- 类型 `54` / `45`：直发 Ark 原生 `/api/v3/contents/generations/tasks`；
- 类型 `46`：进入千帆 FireSeries 转换，提交到 `/beta/video/generations/qianfan-video/fireseries`。

插件会把客户侧的 Seedance 请求转换为上游格式：

- `prompt` → `content: [{type: "text", text: ...}]`；
- `seconds` / `duration` → `duration`；
- 图片引用 → `role: "reference_image"`；
- 视频引用 → `role: "reference_video"`；
- 音频引用 → `role: "reference_audio"`；
- QF 模型映射：2.0 → `S2.0`，2.0 Fast → `S2.0-Fast`，2.0 Mini → `S2.0-Mini`，2.5 → `S2.5`。

AI 网关的完整模型名不能提前改成 `S2.0` 或 `S2.5`；只有进入类型 `46` 的 QF 分支时才做短名称映射。

## 3. 常见错误

### 把 AI 网关当成 QF

对 AI 网关调用：

```text
/beta/video/generations/qianfan-video/fireseries
```

会得到 `404 NOT_FOUND`。这说明路径错，不等于 Key 无效；AI 网关必须使用 `/api/v3/contents/generations/tasks`。

### 把 Ark 的媒体角色原样传给 QF

QF 要求不同媒体角色。插件会将通用请求中的媒体角色转换成 `reference_image`、`reference_video` 和 `reference_audio`。不要在插件外部绕过转换后直接复用 Ark 原始 `role: "reference"`。

### 任务列表为空

创建任务接口和查询接口是异步任务链。提交响应只有任务 ID 时，网页列表必须继续调用查询接口；不能把“暂无视频”当作提交失败，也不能把旧创作页当成任务列表页。

## 4. 测试安全

- 真实视频生成可能产生费用；默认只做配置、端点和协议检查。
- 用户明确要求真实生成时，使用 5 秒、无参考素材的最小请求。
- 输出只记录模型、HTTP 状态、任务 ID 是否存在、任务状态和脱敏错误摘要。
- 不把 `BAIDU_AI_KEY`、QF Token、临时签名视频 URL 或 Cookie 写入 Skill、日志和 Git。
