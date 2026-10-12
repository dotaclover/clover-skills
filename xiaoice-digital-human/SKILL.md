---
name: xiaoice-digital-human
description: 直接调用小冰（微软数字人）官方 OpenAPI 生成数字人播报视频，及形象训练、声音训练。含形象目录查询、视频任务提交与轮询、质检→启动训练→训练结果的状态流程。当用户要求"数字人视频""虚拟人播报""小冰数字人""数字人形象/声音训练"时使用。
agent_created: true
---

# 小冰数字人官方 API

直接调用小冰官方 OpenAPI。接口信息来自三层核实：官方文档（`show/114` 编辑器视频、`show/180` 素材枚举、`show/156` 字体）+ 上游代码（`C://code//cloverapi//extensions//studio//xiaoice//`）+ **实测调用验证**。凡标注「实测」的都是真跑过接口得到的结论；与文档不一致处已注明取舍。

## 两条使用路径（先选路径，再看细节）

这个 API 有两种用法，**能力完全一样，只是调用姿势不同**：

| 路径 | 适用场景 | 怎么用 |
| --- | --- | --- |
| **A. 最简单模式** | 只想「给个形象 + 一段文字 → 出一条播报视频」，占 90% 的真实需求 | 只用 `virtualHuman` + `tts` + `voiceTexts` 三件套，其余字段全省略。见「快速上手」 |
| **B. 编辑器模式** | 需要字幕、图文叠加、多场景、公式、转场等 | 在场景里加 `caption` / `displayTexts` / `displayImages` / `displayVideos` / `backgroundImage` / `transferEffects`。见 `references/editor-mode.md` |

**不要为路径 A 的用户暴露路径 B 的字段。** 编辑器字段相互约束多（zIndex 不能重复、宽高比、时长截断等），暴露给普通用户只会制造失败率和客诉。要支持高级需求就用一个 JSON 输入框透传，见下节。

## 快速上手（路径 A：最简可用请求）

三件套就能出片 —— **这是唯一必须记住的模板**：

```bash
# 1) 取形象详情（拿到 virtualHumanId / 姿态 / 声音）
curl -s -X POST "$BASE/openapi/video/detailDigitalEmployee" \
  -H "Content-Type: application/json" -H "subscription-key: $XIAOICE_KEY" \
  -d '{"bizId":"VHPVCW35N3M8DO0"}'

# 2) 提交（只需 virtualHuman / tts / voiceTexts）
curl -s -X POST "$BASE/openapi/video/task/v2/submit" \
  -H "Content-Type: application/json" -H "subscription-key: $XIAOICE_KEY" \
  -d '{
    "outputVideoName": "demo",
    "outputVideoFormat": "mp4",
    "width": 1080, "height": 1920,
    "creationDetail": { "scenes": [{
      "virtualHuman": {
        "virtualHumanId": "<详情里的 virtualHumanId>",
        "virtualHumanPostureId": "<详情 postureInfos[0].bizId>",
        "zIndex": 20,
        "attributes": {"width":1080,"height":1920,"x":0,"y":0}
      },
      "tts": { "voiceId": "<详情 defaultVoiceId>", "rate":1, "pitch":1, "volume":50 },
      "voiceTexts": ["要播报的文本"]
    }]}
  }'

# 3) 轮询到 finished 后立刻下载（成片链接仅 24 小时有效）
curl -s "$BASE/openapi/video/task/v2/detail?taskId=<taskId>" \
  -H "subscription-key: $XIAOICE_KEY"
```

**唯一必须自己算的是 `attributes` 宽高**（要按姿态预览图等比，见 `references/endpoints.md` 的「画布适配」）。其余字段照抄即可。

## 扩展输入（透传 JSON）

面向普通用户时，**不要做参数面板，做一个 JSON 输入框**：后端只校验白名单字段，其余原样透传进 `creationDetail.scenes[]`。理由：

- 上游字段几十个且互相约束，做 UI 控件等于把上游复杂度搬到前端，且上游一改就得跟改。
- 透传层不承担语义，只做**校验 + 兜底**，维护成本最低。
- 高级用户能直接照着官方文档写 JSON。

透传层**必须**做的最小校验（不做会被上游拒或出坏片）：

| 校验项 | 规则 | 不校验的后果 |
| --- | --- | --- |
| `zIndex` 唯一 | 同场景内虚拟人/字幕/文字/图片/视频的 `zIndex` 互不重复，范围 1–100 | 上游直接报错 |
| 虚拟人宽高比 | 与所选姿态 `previewPicture` 等比 | **视频里人被拉伸变形**（不报错，最坑） |
| 画布尺寸 | `width * height <= 3840 * 2160` 且均为偶数 | 上游报错 |
| `rate`/`pitch`/`volume` | 0.6–1.5 / 0.6–1.5 / 0–100 | 上游报错 |
| 文本长度 | ≤10800 字符 | 上游报错 |
| 素材大小 | 音乐≤50MB、图片≤10MB、视频≤300MB、音频≤100MB | 上游拉取失败 |
| LaTeX 转义 | JSON 中 `\` 必须写成 `\\` | 公式解析错误 |

**兜底策略**：透传字段解析失败时，忽略该字段并用默认值继续生成，**不要整体报错** —— 普通用户看不懂 JSON 报错，直接失败比少个特效糟得多。

## 基础约定

- **Base URL 有两个，功能等价，实测均可调通同一接口**：
  - `https://aibeings-vip.xiaoice.com`（官方文档给出的另一种写法）
  - `https://openapi.xiaoice.com/vh`（**官方文档正式写明的域名前缀**，需与接口路径拼接，大小写不敏感）

  例：`GET https://openapi.xiaoice.com/vh/openapi/customize/zero/res`
  实测两个域名的 `queryDigitalEmployee`、`material/artFontTemplates`、`material/transferEffects` 返回完全一致。渠道可配置，建议做成配置项而非硬编码。
- 鉴权：请求头 `subscription-key: <你的订阅密钥>`，`Content-Type: application/json`。一个密钥对应一个账户，不支持多 Key。
- 统一响应包裹：`{"code": 200, "message": "...", "data": ...}`。**必须检查 `code === 200`**，HTTP 200 不代表业务成功。部分接口还会带 `traceId`，报错时一并记录便于找官方定位。
- 并发：文档同时写了「单个企业 10 路并发」与「默认 20 个并发任务」，以实际账号为准，按 10 保守设计。

## 能力索引（实测通过）

| 能力 | 端点 | 脚本 | 状态 |
| --- | --- | --- | --- |
| 公共形象列表 | `video/queryDigitalEmployee` | `01` | 实测通（184 个，分 2 页） |
| 形象详情 + 画布自算 | `video/detailDigitalEmployee` | `02` | 实测通（自动输出 attributes） |
| 花字 / 转场枚举 | `video/material/artFontTemplates`、`video/material/transferEffects` | `03` | 实测通（59 花字 / 8 转场） |
| 最简生成 | `video/task/v2/submit` | `04` | 实测通（**计费**） |
| 编辑器生成 | 同上 | `05` | 实测通（**计费**） |
| 轮询 + 下载 | `video/task/v2/detail` | `06` | 实测通（**24h 内必须下**） |
| 任务对账 | `video/task/v2/pageQuery` | `07` | 实测通（含时长合计） |
| 移除任务 | `video/task/v2/remove` | `08` | 实测通（**非取消，仍在计费**） |
| 形象训练四步 | `customize/zero/commit` → `get-ckq-result` → `start-training` → `get-training-result` | `09` | 已按文档实现 |
| 声音训练两步 | `customize/zero/voice/commit` → `voice/get-training-result` | `10` | 已按文档实现 |

**共 10 个脚本、 14 个端点，无遗漏。** 占位参数（形象 ID、文本）用 `01`/`02` 查出来后直接填。

## 参考资料

按需加载，不要一次全读：

| 文件 | 内容 |
| --- | --- |
| `references/endpoints.md` | 核心接口：形象查询/详情、任务提交、轮询、任务管理与对账、花字与转场枚举、字体枚举、画布适配公式 |
| `references/editor-mode.md` | 编辑器模式完整字段清单：场景字段总表、图层规则、TTS、自定义音频、字幕、文字/图片/视频素材、LaTeX |
| `references/layout-pitfalls.md` | 版式实测与 6 个坑：标题折行、字幕居中、字宽计算、抽帧验证 |
| `references/dialogue-video.md` | 多角色双人对谈方案、坐标模板、背景图不可用的实测结论、字幕词中截断 |
| `references/training.md` | 形象训练三步流程、声音训练两步流程、训练素材要求 |
| `references/assets-and-timing.md` | 素材准备与上限、小冰 CDN 域名限制、字段名速查、时长预估标定 |

## 执行步骤（Agent 使用）

1. 先查形象列表和详情，拿到 `bizId` → `virtualHumanId`、姿态、声音（`references/endpoints.md`）。
2. 提交任务，记录返回的 bizId/taskId，按 10–30 秒间隔轮询。
3. 训练类任务耗时较长，轮询间隔可放宽到 60 秒以上；质检通过后**不要忘记**调用 `start-training`（`references/training.md`）。
4. 成片/训练结果 URL 及时下载转存。
5. 用 present_files 展示下载到本地的视频文件。

注意：训练素材必须是无内嵌账号密码的绝对 HTTP(S) URL 且上游可访问；同一账户同类训练进行中时不要重复提交。
