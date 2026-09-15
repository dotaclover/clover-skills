---
name: xiaoice-digital-human
description: 直接调用小冰（微软数字人）官方 OpenAPI 生成数字人播报视频，及形象训练、声音训练。含形象目录查询、视频任务提交与轮询、质检→启动训练→训练结果的状态流程。当用户要求"数字人视频""虚拟人播报""小冰数字人""数字人形象/声音训练"时使用。
---

# 小冰数字人官方 API

直接调用小冰官方 OpenAPI。接口信息来自三层核实：官方文档（`show/114` 编辑器视频、`show/180` 素材枚举、`show/156` 字体）+ 上游代码（`C://code//cloverapi//extensions//studio//xiaoice//`）+ **实测调用验证**。凡标注「实测」的都是真跑过接口得到的结论；与文档不一致处已注明取舍。

## 两条使用路径（先选路径，再看细节）

这个 API 有两种用法，**能力完全一样，只是调用姿势不同**：

| 路径 | 适用场景 | 怎么用 |
| --- | --- | --- |
| **A. 最简单模式** | 只想「给个形象 + 一段文字 → 出一条播报视频」，占 90% 的真实需求 | 只用 `virtualHuman` + `tts` + `voiceTexts` 三件套，其余字段全省略。见「快速上手」 |
| **B. 编辑器模式** | 需要字幕、图文叠加、多场景、公式、转场等 | 在场景里加 `caption` / `displayTexts` / `displayImages` / `displayVideos` / `backgroundImage` / `transferEffects`。见「编辑器模式：完整功能清单」 |

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

**唯一必须自己算的是 `attributes` 宽高**（要按姿态预览图等比，见「画布适配」）。其余字段照抄即可。

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


- **Base URL 有两个，功能等价，实测均可调通同一接口**：
  - `https://aibeings-vip.xiaoice.com`（官方文档给出的另一种写法）
  - `https://openapi.xiaoice.com/vh`（**官方文档正式写明的域名前缀**，需与接口路径拼接，大小写不敏感）

  例：`GET https://openapi.xiaoice.com/vh/openapi/customize/zero/res`
  实测两个域名的 `queryDigitalEmployee`、`material/artFontTemplates`、`material/transferEffects` 返回完全一致。渠道可配置，建议做成配置项而非硬编码。
- 鉴权：请求头 `subscription-key: <你的订阅密钥>`，`Content-Type: application/json`。一个密钥对应一个账户，不支持多 Key。
- 统一响应包裹：`{"code": 200, "message": "...", "data": ...}`。**必须检查 `code === 200`**，HTTP 200 不代表业务成功。部分接口还会带 `traceId`，报错时一并记录便于找官方定位。
- 并发：文档同时写了「单个企业 10 路并发」与「默认 20 个并发任务」，以实际账号为准，按 10 保守设计。

## Skill 覆盖自检（实测通过）

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

## 素材准备

**官方没有素材上传接口**，所有素材都用 `mediaUrl` 直接引用现成 URL。这意味着素材必须**公网可访问**且是直链（不能带鉴权、不能是页面地址）。

| 素材类型 | 字段 | 格式与上限 |
| --- | --- | --- |
| 背景音乐 / 场景音乐 | `backgroundMusic.mediaUrl` | MP3、WAV，≤50MB |
| 背景图片 | `backgroundImage.mediaUrl` | JPG、PNG、GIF，≤10MB |
| 文字素材 | `displayTexts[].content` | 纯文本，无上传 |
| 图片素材 | `displayImages[].mediaUrl` | JPG、PNG、GIF，≤10MB |
| 视频素材 | `displayVideos[].mediaUrl` | MP4，≤300MB |
| 自定义音频（替代 TTS） | `scenes[].voiceUrl` | MP3、WAV，≤100MB |
| 自定义字体 | `attributes.fontPath` | 字体文件如 `https://xxx.ttf` |
| 形象/声音训练素材 | `trainingVideoUrl` / `trainingAudioUrl` | 也必须是公网直链 |

自建服务时，用 Nginx 反代一个 `/uploads/` 公开目录即可满足（见 `scripts/deploy-nginx.conf` 示例）。

## 视频生成

### 1. 查询形象（数字员工）

```json
POST /openapi/video/queryDigitalEmployee
{ "categoryList": [0], "modelType": "STUDIO", "pageIndex": 1, "pageSize": 100 }
```

返回 `data: {records: [{bizId, name, category, summaryImage, summaryVideo}], total, pages}`。`categoryList: [0]` 为官方公共形象；分页取完所有页，总数以 `total` 为准。

### 2. 形象详情（获取 virtualHumanId 与可选声音/姿态）

```json
POST /openapi/video/detailDigitalEmployee
{ "bizId": "<形象的bizId>" }
```

返回 `data`：

| 字段 | 说明 |
| --- | --- |
| `virtualHumanId` | 提交视频时必须使用此 ID，**不是** bizId |
| `defaultVoiceId` | 默认声音 |
| `postureInfos` | `[{bizId, name, previewPicture}]`，姿态用 `bizId` |
| `voiceInfos` | `[{voiceId, displayName, language, gender, auditionFile}]` |

### 3. 提交视频任务

```json
POST /openapi/video/task/v2/submit
{
  "outputVideoName": "示例视频",
  "outputVideoFormat": "mp4",
  "aigcWatermark": false,
  "width": 1080,
  "height": 1920,
  "creationDetail": {
    "scenes": [{
      "virtualHuman": {
        "virtualHumanId": "<来自详情>",
        "virtualHumanPostureId": "<来自详情 postureInfos.bizId，缺省用第一个>",
        "zIndex": 20,
        "attributes": { "width": 1080, "height": 1920, "x": 0, "y": 0 }
      },
      "tts": { "voiceId": "<voiceInfos.voiceId 或 defaultVoiceId>", "rate": 1, "pitch": 1, "volume": 50 },
      "voiceTexts": ["这里是数字人的播报文本。"]
    }]
  }
}
```

- 成功返回 `data` 为**任务 ID 字符串**（实测）；官方文档（数字员工企业版 show/114）标注为 `{"id": "<任务ID>"}` 对象。**两种形态都要兼容解析**，不要写死。
- 播报文本 1–10800 字符；时长预估 = 字符数 ÷ 语速（字/秒），向上取整，上限 3600 秒。
- `width`/`height` 是**顶层输出画布**设置，默认 1920×1080，约束 `width * height <= 3840 * 2160` 且必须为偶数。竖屏用 1080×1920。
- ⚠️ `virtualHuman.attributes` 的 `width`/`height` **必须与所选姿态的 `previewPicture` 保持原始宽高比**，否则虚拟人会被拉伸变形。姿态预览图的宽高直接编码在 URL 里（形如 `..._2160x3840.webp`），按等比缩放居中计算：
  - 例：画布 1080×1920，姿态图 944×1080 → `width=1080, height=1236, x=0, y=342`
  - 例：画布 1080×1920，姿态图 720×1280（9:16）→ `width=1080, height=1920, x=0, y=0`
  - 官方原话：「放缩时请保持虚拟人的宽高比不变，否则会被拉伸变形」。
- `voiceId` 必须属于该形象（voiceInfos 或默认），姿态必须属于 postureInfos。
- `zIndex` 同一场景内不可重复、须 >1、范围 1–100。
- 官方文档还支持（本 skill 未覆盖的进阶用法）：`voiceUrl` 用已有音频驱动（此时自动字幕失效，音频时长决定场景时长）、`backgroundMusic`、`displayTexts`/`displayImages`/`displayVideos`、`caption` 字幕、`transferEffects` 转场、`hasLatex` + `latexStyle` 公式、`outputVideoName`（≤100 字）。

### 4. 轮询任务

```json
GET /openapi/video/task/v2/detail?taskId=<任务ID>
```

`data` 字段：`status`、`progress`（0–1 小数）、`videoUrl`、`videoThumbnailImageUrl`、`videoDurationMilliseconds`、`videoSizeBytes`、`error`、`createTime`、`finishTime`、`clientType`。

- **`status` 枚举：官方文档为 `running`（创建中）/ `finished`（完成）/ `error`（失败）**。历史版本和不同接口出现过 `queued`/`processing`/`failed`，判断时要做宽松匹配（大小写、空白也归一化）。**只判断 `failed` 会漏掉 `error`，导致失败任务永远停在「进行中」、预扣额度不退。**
- `finished` 才有 `videoUrl`，立即下载转存，不要把 URL 当长期地址。
- 失败时看 `data.error` 或 `message`。
- 计费按实际时长：`ceil(videoDurationMilliseconds / 1000)` 秒，上限 3600。
- `data` 实测是对象，官方文档标注为数组 —— 两种都要兼容。

### 4.1 删除任务与任务列表（官方文档有，常被忽略）

```json
POST /openapi/video/task/v2/remove
{ "taskIds": ["<任务ID>", "<任务ID>"] }     // 批量删除，返回 code 200

POST /openapi/video/task/v2/pageQuery
{ "pageIndex": 1, "pageSize": 50 }          // 列出企业下全部任务
```

`pageQuery` 可选过滤：`userId` / `userEmail` / `userPhone`（三者只需传一个；都不传则返回企业下所有任务）。

返回 `data` 是 `Page` 对象：`{current, size, total, pages, records[]}`，`records[]` 与轮询接口的 `VideoTaskResult` 同构。**这是对账上游真实用量的唯一途径** —— 把全量 `videoDurationMilliseconds` 求和即可核对实际消耗（比逐任务轮询可靠得多）。

#### ⚠️ `remove` 不是「取消任务」（实测结论）

实测：调 `remove` 后任务**立即从 `pageQuery` 列表中消失**（total 从 46 降到 45），但

```
GET /openapi/video/task/v2/detail?taskId=<已remove的任务>   →   status = running
```

**任务本身仍在后台继续生成**。所以：

| 用途 | 是否可行 |
| --- | --- |
| 清理任务列表、隐藏测试任务 | ✅ 可以 |
| 取消正在生成的任务、止损 | ❌ **不行**，上游会继续跑 |
| 停止计费 | ❌ **不行** |

**小冰目前没有暴露真正的取消接口。** 已提交的任务只能等它跑完并承担费用。这直接决定了产品设计：*无法靠事后取消来兜底，必须在提交前把额度校验做严*，否则超额支出不可撤回。

### 4.2 视觉素材枚举（写死不如实时拉取）

```json
GET /openapi/video/material/artFontTemplates    // 花字模板列表
GET /openapi/video/material/transferEffects     // 转场动画列表
```

无请求参数。**实测已确认可用**（两个域名均返回 code 200）：

- **花字模板 59 个**，`data[].name` + `data[].preview`（预览图 url）。命名分四组：`MHM_1..MHM_16`、`MM_1..MM_17`、`MH_1..MH_16`、`HM_1..HM_10`。用在 `displayTexts[].artFontTemplateName`。
- **转场动画 8 个**，`data[].type` + `data[].name` + `data[].previewGif`：

| type | 名称 |
| --- | --- |
| `wipe_left` | 向左擦除 |
| `wipe_right` | 向右擦除 |
| `wipe_up` | 向上擦除 |
| `clock_rotation` | 时钟旋转 |
| `grid` | 栅格 |
| `circular_scanning` | 圆形扫描 |
| `circular_in` | 圆形收缩 |
| `circular_out` | 圆形展开 |

用在 `scenes[].transferEffects[].type`。**注意：官方文档说「转场动画」是场景之间的过渡，但 `transferEffects` 挂在 `scenes[]`（场景内）而非场景数组之间** —— 实测挂在 scene 内可正常出片。

### 4.3 字体枚举（`attributes.font` 用序号）

`font` 字段取**字体序号整数**，共 112 个。常用：

| 序号 | 字体 | 序号 | 字体 |
| --- | --- | --- | --- |
| 1 | 方正黑体简体 | 6 | 微软雅黑（**默认值**） |
| 2 | 方正楷体简体 | 7 | 未来圆 SC |
| 3 | 方正宋体简体 | 10 | 思源黑体 |
| 4 | 文泉驿微米黑 | 11 | 思源宋体 |
| 5 | 文泉驿等宽正黑 | 12 | 楷体 GB2312 |

13–103 为各类手写/美术/花体中文（阿里巴巴普惠体M、思源简体、阿里妈妈数黑体、汉标系列、南构系列、叶根友系列等）；104–112 为多语言字体（`Nom Na Tong`、`Boon`、`Gulzar`、`UKIJEs` 系列维吾尔文等）。完整表见官方文档 `show/156`，预览图包：`https://virtualman.oss-cn-beijing.aliyuncs.com/media_upload/material/12aff38a51da4e19af62dbaf9f19d5a7.zip`。

需要精确指定时，也可用 `attributes.fontPath` 直接给字体文件 URL。

## 编辑器模式：完整功能清单

普通播报只用 `virtualHuman` + `tts` + `voiceTexts`。但 `scenes[]` 实际是一个**完整的视频编辑器场景**，下面是全部可用字段（**空场景 = 需要至少一个非空场景**）。

### 场景字段总表（`OpenApiScene`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `virtualHuman` | object | 是 | 虚拟人，见下 |
| `tts` / `voiceUrl` | object / string | 二选一 | TTS 合成 / 用已有音频驱动，见下 |
| `voiceTexts` | string[] | 用 tts 时必填 | 播报内容，`arraySize > 0`，不允许空串或 null |
| `hasLatex` | boolean | 否 | `voiceTexts` 是否按 LaTeX 处理，见下 |
| `caption` | object | 否 | 字幕，见下 |
| `displayTexts` | object[] | 否 | 叠加文字素材（可用花字模板），见下 |
| `displayImages` | object[] | 否 | 叠加图片素材，见下 |
| `displayVideos` | object[] | 否 | 叠加视频素材，见下 |
| `backgroundImage` | object | 否 | 场景背景图（自动拉伸覆盖全屏），为空则填白。**⚠️ 实测行为与文档不符，见下方「多角色对话视频」** |
| `backgroundMusic` | object | 否 | 场景背景音乐，**存在全局背景音乐时此项失效** |
| `transferEffects` | object[] | 否 | 转场动画，`{type, duration}` 均必填 |

### 顶层与全局

| 字段 | 说明 |
| --- | --- |
| `outputVideoName` | **必填**，≤100 字 |
| `outputVideoFormat` | 枚举 `mp4` / `mkv`，默认 `mp4`，必须小写 |
| `width` / `height` | 输出画布，默认 `1920` / `1080`；约束 `width * height <= 3840 * 2160` **且必须为偶数** |
| `aigcWatermark` | AI 水印标识，默认 `false` |
| `creationDetail.backgroundMusic` | **全局**背景音乐，设置后所有场景内 `backgroundMusic` 全部失效 |

`OpenApiBackgroundMusic`：`mediaUrl`（必填）、`volume`（0–1，float，1=原始音量）、`speed`（0–3，float）、`loop`（默认 `true`）。

### 虚拟人（`OpenApiVirtualHuman`）

`virtualHumanId`（来自 `detailDigitalEmployee`）、`virtualHumanPostureId`（姿态 `bizId`，必填）、`zIndex`（必填，1–100）、`attributes`（必填）。

`attributes` 四字段 `width` / `height` / `x` / `y` 全必填。**⚠️ 宽高必须与所选姿态的 `previewPicture` 保持原始宽高比，否则虚拟人会被拉伸变形**（详见下方「画布适配」）。

> 想让虚拟人「不出镜」：把 `x`/`y` 移到画布外，或用图层遮挡。

### 图层规则（所有素材共用）

- `zIndex` 取值 **1–100**，可以不连续。
- **同一场景内所有素材的 `zIndex` 不能重复**（虚拟人、字幕、文字、图片、视频一起算）。
- 序号**大的在上层**，小的在下层。
- `backgroundImage` 固定占用 `zIndex = 1`。

这条例最容易踩：多个素材时随手写相同 zIndex 会被上游拒。

> **⚠️ 实测补充（`zIndex` 唯一性只在同类型素材间生效）**
> - `scene.backgroundImage` **不受 zIndex 影响**：实测把它的 zIndex 设为 5/10/90、
>   虚拟人设为 3/20/50，成片**完全相同**——图片恒定盖在虚拟人之上，等于一层
>   **前景遮罩**，不是背景。官方文档称其为「场景背景图（自动拉伸覆盖全屏）」，
>   **与实测不符**。
> - 因此想给对谈/播报视频加「背景」，**不要用 `backgroundImage`**。
>   可行做法：用 `displayImages`（图片素材，zIndex 可小于虚拟人）垫底，
>   或者干脆保留纯白/纯色底。
> - `displayTexts` 数组内多个元素的 zIndex **也必须互不相同**，
>   否则报 `420 图层序号错误`（实测：两个名牌同写 30 → 420；改成 30/31 → 200）。

### TTS（`OpenApiTts`）

| 字段 | 必填 | 取值 |
| --- | --- | --- |
| `voiceId` | 是 | `detailDigitalEmployee` 的 `VoiceInfo.voiceId` |
| `rate` | 否 | 语速，默认 `1`，**0.6 ≤ rate ≤ 1.5** |
| `pitch` | 否 | 语调，默认 `1`，**0.6 ≤ pitch ≤ 1.5** |
| `volume` | 否 | 音量，默认 `50`，**0 ≤ volume ≤ 100** |
| `latexStyle` | 否 | 公式样式，见下 |

### 自定义音频驱动（替代 TTS）

`scenes[].voiceUrl` 给一个音频 URL（MP3/WAV，≤100MB）即可用现成音频驱动虚拟人。

- 与 `tts` **二选一**。
- **音频时长直接决定场景时长**（不是文本长度）。
- ⚠️ **选用自定义音频后，自动字幕（`caption`）会失效。**

### 字幕（`OpenApiCaption`）

```json
"caption": { "zIndex": 60 }
```

`zIndex` 必填。`topLeft` / `topCenter` / `topRight` 三选一，**全 `false` 时默认居中**。`attributes` 复用 `OpenApiDisplayTextAttributes`。

- 组件宽度自动计算为 **17 个字（含字间距）**，单位像素 —— 宽度会影响居中/居左/居右的实际效果。
- 不填 `attributes` 时：画面居中，y 轴底部留白 1 倍字号，字体默认 6（微软雅黑），字间距 0，字号 40px。

带样式的字幕示例：

```json
"caption": {
  "topLeft": true,
  "zIndex": 60,
  "attributes": {
    "x": 0, "fontColor": "#ff3c3c", "spacing": 5,
    "italic": false, "underline": false, "bold": true, "fontSize": 50
  }
}
```

### 文字素材（`OpenApiDisplayText`）

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `content` | 是 | 文本内容 |
| `zIndex` | 是 | 1–100 |
| `attributes` | 是 | 见 `OpenApiDisplayTextAttributes` |
| `artFontTemplateName` | 否 | 花字模板名，取自 `material/artFontTemplates`，如 `MHM_1` |
| `effectIn` | 否 | `{type, duration}`，入场特效 |
| `effectOut` | 否 | `{type, duration}`，出场特效 |

**入场特效 `effectIn.type` 枚举**：`blur_in`、`slide_right_in`、`slide_left_in`、`sunrise_in`、`zoomout_in`、`zoomin_in`、`slide_down_in`、`slide_up_in`

**出场特效 `effectOut.type` 枚举**：`slide_up_out`、`slide_down_out`、`zoomin_out`、`sunset_out`、`slide_left_out`、`slide_right_out`、`blur_out`

`duration` 为 float 秒，支持两位小数，默认 `3`。**超过场景时长会导致动画被截断**。

### 文字/字幕属性（`OpenApiDisplayTextAttributes`）

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `x` / `y` | 是* | 原点左上角；*作 `caption.attributes` 时非必填（自动居中 / 默认底部留白一号字高） |
| `font` | 是 | 字体序号 1–112，见「字体枚举」 |
| `fontSize` | 是* | 1–200，默认 40；*作 caption 时非必填 |
| `fontColor` | 是 | 十六进制字符串，如 `"0x000000"` ~ `"0xFFFFFF"`；示例中也用 `"#ff3c3c"` 形式 |
| `fontColorOpacity` | 否 | 0–1，默认 1 |
| `angle` | 否 | 顺时针角度，取值 `0` / `90` / `180` / `270`，默认 0 |
| `bold` / `italic` / `underline` | 否 | 默认 false |
| `spacing` | 否 | 字间距，默认 0 |
| `fontPath` | 否 | 自定义字体源 URL，如 `https://xxx.ttf` |
| `shadowOn` / `shadowColor` / `shadowOffsetX` / `shadowOffsetY` | 否 | 阴影 |
| `strokeOn` / `strokeColor` / `strokeWidth` | 否 | 描边。`strokeColor` 用 RGBA 如 `#f0f0f0f0`；**花字模板自带描边，一旦这里显式传了 `strokeOn`（true/false 都算），就会覆盖模板的描边设置** |
| `backgroundColor` / `radius` | 否 | 背景色（RGBA）/ 背景圆角 |

### 图片素材（`OpenApiDisplayImage`）

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `mediaUrl` | 是 | JPG/PNG/GIF，≤10MB |
| `zIndex` | 是 | 1–100，不重复 |
| `attributes` | 是 | `width`、`height`、`x`、`y` 全必填；`opacity`（0–1，默认 1）、`rotation`（`0`/`90`/`180`/`270`，默认 0）可选 |

`x`/`y` 不设置时元素处于**画面正中心**。

### 视频素材（`OpenApiDisplayVideo`）

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `mediaUrl` | 是 | MP4，≤300MB |
| `zIndex` | 是 | 1–100，不重复 |
| `attributes` | 是 | 见下 |
| `coverUrl` | 否 | 封面图 url |

`OpenApiDisplayVideoAttributes`：`width` / `height` / `x` / `y`（必填，非等比缩放结果须 > 10）、`durationMilliseconds`（**文档标注为必填**：老引擎依赖，官方说下个版本会修复、不再必填 —— 当前建议照传）、`volume`（0–1）、`loop`。

⚠️ **视频素材无法自动截断，会按顺序依次播放完**，规划时长时要计入。

### LaTeX 公式

`hasLatex: true` 开启（`voiceTexts` 含公式时建议显式传）。支持四种包围格式：`$...$`、`$$...$$`、`\(...\)`、`\[...\]`。

开启后 **音频按公式读法播报，字幕/画面仍保留公式渲染效果**。

⚠️ **JSON 中反斜杠必须转义**：LaTeX `\frac{x}{n}` 要写成 `\\frac{x}{n}`。文档示例中的 `\\sum`、`\\limits`、`\\frac` 都是转义后的写法。

公式样式用 `tts.latexStyle`（**与普通文本样式分开**）：

| 字段 | 说明 |
| --- | --- |
| `fontSize` / `fontColor` / `fontColorOpacity` / `maxWidth` | 字号 / 主色 / 透明度 / 最大展示宽度 |
| `backgroundColor` / `radius` | 背景色 / 圆角 |
| `shadowOn` / `shadowColor` / `shadowOffsetX` / `shadowOffsetY` | 阴影 |
| `strokeOn` / `strokeColor` / `strokeWidth` | 描边 |

> `latexStyle` 只管公式渲染效果；普通字幕/文字的排版（位置、字体、字间距、旋转、加粗斜体下划线）看 `caption.attributes` / `displayTexts[].attributes`。同一场景两者都有时，各配各的。

### 版式实测：标题 + 字幕（逐像素量测，竖屏 1080x1920）

这一节是**真跑出片 + 读像素量出来的**，不是照抄文档。文档在这个话题上有多处与事实不符，照抄必踩坑。

| 元素 | 字段 | 实测值 | 量测依据 |
| --- | --- | --- | --- |
| 标题 | `displayTexts[0].attributes.y` | **200** | 白字顶边落在 212，视觉靠顶合适 |
| 标题 | `fontSize` | 76 | |
| 标题 | 折行上限 | 3 行 / 40 字 | 折行后受行数限制实际约 36 字 |
| 标题 | 单行宽度上限 | 画布 90%（竖屏 972px） | 超出会被两侧裁切 |
| 字幕 | `caption.attributes.y` | **1780** | 底框底边落在 1847，**离底 73px** |
| 字幕 | `caption.attributes.y` 安全上限 | **1829** | y=1830 → 离底仅 23px 已贴死；y≥1850 下半截被裁 |
| 字幕 | `fontSize` | 52 | 字幕框高度占用 ≈67px |

#### 坑 1：标题不会自动折行

实测 21 字标题**直接横穿画面被两侧裁切**，没有任何警告。必须自己插 `\n` 断行：

```python
def wrap_title(title, font_size, canvas_w=1080, ratio=0.90, max_lines=3):
    limit = canvas_w * ratio
    lines, cur, cur_w = [], "", 0.0
    for ch in title:
        cw = font_size if ord(ch) > 0x2E80 else font_size * 0.5
        if cur and cur_w + cw > limit:
            lines.append(cur); cur, cur_w = ch, cw
        else:
            cur += ch; cur_w += cw
    if cur: lines.append(cur)
    lines = lines[:max_lines]
    # 均衡化：把最长行末字挪给最短行，直到行宽差 < 1 个字号
    while len(lines) > 1:
        widths = [len([c for c in l]) * font_size for l in lines]  # 简化示意
        mx, mn = widths.index(max(widths)), widths.index(min(widths))
        if mx == mn or len(lines[mx]) <= 1 or max(widths) - min(widths) <= font_size:
            break
        lines[mn] += lines[mx][-1]; lines[mx] = lines[mx][:-1]
    return "\n".join(lines)
```

#### 坑 2：多行标题不居中

多行时**各行左对齐于同一个 x**，短行不会自动居中。解法是上面的「均衡断行」——让各行像素宽度尽量相等，左对齐的观感就接近居中。实测 21 字断成 722 / 684 两行，观感居中良好。

#### 坑 3：字幕不传 x/y 就完全不显示

⚠️ **与文档矛盾**。文档说「不填 `attributes` 时默认画面居中、y 轴底部留白一号字高」，**实测成片里字幕完全不出现**。

必须 `topLeft: true` 且显式传 `x`、`y`：

```json
"caption": {
  "topLeft": true,
  "zIndex": 60,
  "attributes": {
    "x": 280, "y": 1780,
    "font": 6, "fontSize": 52, "fontColor": "#FFFFFF", "bold": true,
    "backgroundColor": "#1677FFCC", "radius": 12
  }
}
```

只传 `topCenter: true` + `zIndex`（无 attributes）→ 空白。只传 `topLeft` 不传 x/y → 空白。

#### 坑 4：居中要自己算字宽

上游**没有 text-align 参数**，`x` 一律是文字块左上角。ASCII 半角和 CJK 全角宽度不同：

```python
def text_width(text, font_size, spacing=0.0):
    # CJK 及全角标点 ≈ 1.0 倍字号；ASCII 半角 ≈ 0.5 倍
    return sum((font_size + spacing) if ord(c) > 0x2E80 else (font_size * 0.5 + spacing)
               for c in text)

def center_x(text, font_size, spacing=0.0, canvas_w=1080):
    return max(0, int((canvas_w - text_width(text, font_size, spacing)) / 2))
```

实测：纯中文按 1.0 倍算出的 x 完全居中；「2026 产品发布会」若把数字也按 1.0 倍算，标题会明显偏右。

#### 坑 5：字幕 x 要按「实际文案」算，不是按「17 字组件」算

文档说字幕组件宽度固定 17 个字。但**字幕是从 x 起左对齐排字，不是以 x 为左边界居中排列**。

- 按 17 字宽算得 `x=98` → 成片字幕**明显偏左**
- 按实际首句文案宽算得 `x=280` → 完全居中

所以要用播报文本的首句（在标点处断句）来估宽度。

#### 坑 6：抽帧验证别用 `-ss`

`ffmpeg -ss 2` 会落在关键帧之间导致**输出空文件**。改用帧序号：

```bash
ffmpeg -y -i out.mp4 -vf "select=eq(n\,5)" -frames:v 1 -vsync 0 frame.png
```

#### 成本提示

`displayTexts` / `caption` **不计费**，只有 `voiceTexts` 的语音时长计费。
做版式实验时把 `voiceTexts` 设为 `["你好"]` 即可产出约 0.76 秒的片子，**1 钻石一条**，标题随便测多长都免费。

### 画布适配（虚拟人宽高比）

虚拟人 `attributes` 的宽高必须与所选姿态的 `previewPicture` 等比。宽高**编码在预览图 URL 里**：

```
https://virtualman.oss-cn-beijing.aliyuncs.com/vhop/1765854225680/CNe26aRhlmdF_2160x3840.webp
                                                                              ^^^^^^^^^^^ 宽 x 高
```

缩放公式（等比 + 居中，结果取偶数）：

```
scale = min(canvasW / srcW, canvasH / srcH)
width  = even(srcW * scale)
height = even(srcH * scale)
x = (canvasW - width) / 2
y = (canvasH - height) / 2
```

**官方文档给出的标准例子（可用作自测）**：画布 `1080 × 1920`，姿态预览图 `944 × 1080` → 结果必须是 `width=1080, height=1236, x=0, y=342`。

实测三种常见姿态图尺寸的换算结果：

| 姿态图 | 画布 1080×1920 下的结果 |
| --- | --- |
| `720 × 1280`（9:16） | `1080 × 1920` at `(0, 0)`，铺满 |
| `944 × 1080` | `1080 × 1236` at `(0, 342)` |
| `2160 × 3840`（9:16） | `1080 × 1920` at `(0, 0)`，铺满 |

## 多角色对话视频（双人对谈）

把一个形象当一个人用太浪费。**同一条视频里演一场双人对谈**是这套 API 最容易被忽略的能力，实测可行，方案如下。

### 核心限制与对策

| 限制（实测） | 对策 |
| --- | --- |
| 一个 `scene` 只能有一个 `virtualHuman`（传数组报 `407 非法的请求体`） | 用 `scenes[]` 逐句切场景，**每句都是独立场景** |
| 逐场景切换会让虚拟人「原地变脸」，观感等于一个人在自问自答 | **给每个角色分配固定坐标**（A 左上、B 右下），场景切换时只有人变、位置不变 |
| 账号内可能只有一个男性形象 | 用**同一形象的两种姿态**当两个人（`postureInfos` 常有 4–44 个，如「潮人-聆听」「老板-聆听」），视觉差异明显 |
| 形象自带音色可能只有一种 | 音色池里有**公共音色** `101-wenyou`（男）、`101-*` 系列，任意形象都可用；账号内音色大多也支持 `zh-CN / zh-HK / en-US` 三语，念英文无需换音色 |

### 坐标模板（竖屏 1080×1920，两人各占一角）

```python
BOX_W, BOX_H = 430, 764        # 720×1271 姿态图等比缩放到 430 宽
TOM_BOX   = (55, 470)          # 左上
JERRY_BOX = (595, 990)         # 右下
```

每个场景里：

```python
scene = {
    "virtualHuman": {
        "virtualHumanId": VID,
        "virtualHumanPostureId": POS_TOM if who == "Tom" else POS_JERRY,
        "zIndex": 20,
        "attributes": {"x": TOM_BOX[0], "y": TOM_BOX[1], "width": BOX_W, "height": BOX_H},
    },
    "tts": {"voiceId": VOICE, "rate": 1, "pitch": 1, "volume": 50},
    "voiceTexts": [text],
    "caption": { ... },                      # 每句自己的字幕，位置固定
    "displayTexts": [                        # 两个名牌常驻，说话方高亮
        {"content": "Tom",   "zIndex": 30, "attributes": {name_attrs(C_TOM if who=="Tom" else C_DIM)}},
        {"content": "Jerry", "zIndex": 31, "attributes": {name_attrs(C_JERRY if who=="Jerry" else C_DIM)}},
    ],
}
```

名牌的 zIndex 必须一个 30、一个 31 之类**互不相同**，否则 `420 图层序号错误`。

说话方高亮（`#FFE400` 黄 / `#4DD0FF` 蓝），非说话方压暗成 `#8C97A6`——观众一眼知道谁在说。

### 实测效果

4 场景 × 约 4 秒 ≈ **15 秒**，11 MB，1080×1920。同一形象的「潮人装」与「西装」两个姿态分别出现在左上、右下，切场景时人物不同、位置不动，能明确读出「两个人在对话」。

### 成本

每个场景的 `voiceTexts` 独立计费，总时长 = 各场景时长之和，与单场景等字数成本相同。**字幕、名牌、坐标全部免费**，只有语音计费。

### 字幕词中截断（英文长句必踩）

上游成片字幕是**按语音切句 + 按字符宽度硬换行**，**不在词边界断**。英文长句会出现：

```
sounds nice. Are you enjoying the s
lower pace
```

中文因为每字等宽不太明显，**英文尤其难看**。缓解办法：把长句拆成两个较短的 `voiceTexts` 项，或把关键停顿写成分句标点让上游切得短一些。

> 实测确认：`voiceTexts` 里手插 `\n` **不会**改变成片字幕的换行位置。
> 对照组 `"...enjoying the slower pace"` 与 `"...enjoying\nthe slower pace"` 的成片字幕
> **完全一致**，都是 `the s / lower pace`。字幕由上游按语音重新切句生成，客户端无法干预换行。

### 媒体资源限制（重要）

`displayImages` / `backgroundImage` 的 `mediaUrl` **只接受小冰自家 CDN 域名的图片**：

| 图片源 | 结果 |
| --- | --- |
| `virtualman.oss-cn-beijing.aliyuncs.com/...` | ✅ 200 |
| `images.unsplash.com/...` | ❌ 410 媒体资源url错误 |
| `picsum.photos/...` | ❌ 410 媒体资源url错误 |

也就是说**要给视频加背景/贴图，必须先把图片传到小冰的 OSS**。
工作台的 `/api/upload` 走的是「本地存储 + 公网 URL」路线，需要配 `PUBLIC_BASE_URL`，
**但这条路产出的 URL 不是小冰 CDN 域名，上游同样会 410**。

> 结论：当前账号下**没有可直接使用的背景图能力**。可行的只有：
> ① 纯白底；② 用小冰 CDN 上已有的图（如形象预览图）当贴图，但它是前景图层，盖住人不好看。
> 若要真正的背景，需要向小冰申请素材上传接口 / OSS 直传能力。

### 字段名速查（易错）

| 素材 | 正确的资源字段 | 错误写法 |
| --- | --- | --- |
| `scene.backgroundImage` | `{mediaUrl, zIndex}` | `{url}` / `{imageUrl}` → 410；直接传字符串 → 407 |
| `displayImages[]` | `{mediaUrl, zIndex, attributes}` | `{url}` → 410 |
| `creationDetail.backgroundMusic` | `{mediaUrl, volume, speed, loop}` | — |

**不同形象的姿态图尺寸并不一致**（实测形象 `VHPVCW35N3M8DO0` 是 720×1280，形象 `VHPBL0UBK89PAV6` 是 2160×3840），所以**不能写死 1080×1920** —— 这是最容易出的画质问题。

## 形象训练（三步流程）

1. **提交**：

```json
POST /openapi/customize/zero/commit
{ "vhModelType": "STUDIO", "trainingVideoUrl": "https://...", "authVideoUrl": "https://...", "voiceTemplateVersion": 1 }
```

返回 `data` 为训练任务 bizId。

2. **质检轮询**：`GET /openapi/customize/zero/get-ckq-result?bizId=<bizId>`
   - `data.status`：`0` 进行中（含 progress）、`1` 质检通过、`-1` 失败（看 `data.message`）。

3. **质检通过后启动训练**（质检通过不会自动开始训练，必须显式调用）：

```json
POST /openapi/customize/zero/start-training
{ "bizId": "<训练bizId>", "name": "我的形象", "voiceBizId": "可选，绑定已完成的声音训练" }
```

4. **训练结果轮询**：`POST /openapi/customize/zero/get-training-result`，body `{"bizId": "<训练bizId>"}`
   - `data.status`：`0` 训练中、`1` 成功（`data.bizId` 为新形象的 bizId，用于后续视频生成）、`-1` 失败。

## 声音训练（两步流程）

1. **提交**：

```json
POST /openapi/customize/zero/voice/commit
{ "name": "我的声音", "trainingAudioUrl": "https://...", "languageType": "CHINESE", "audioText": "可选，录音文字" }
```

- `languageType`：`CHINESE` 或 `MULTI`；`MULTI` 可加 `"reduceNoise": 0|1`。
- 成功返回 `data` 为训练任务 bizId。

2. **结果轮询**：`POST /openapi/customize/zero/voice/get-training-result`，body `{"bizId": "<bizId>"}`
   - `status` 同上；成功时 `data.voiceBizId` 用于形象训练绑定，**不是** `bizId`。

## 执行步骤（Agent 使用）

1. 先查形象列表和详情，拿到 `bizId` → `virtualHumanId`、姿态、声音。
2. 提交任务，记录返回的 bizId/taskId，按 10–30 秒间隔轮询。
3. 训练类任务耗时较长，轮询间隔可放宽到 60 秒以上；质检通过后不要忘记调用 start-training。
4. 成片/训练结果 URL 及时下载转存。
5. 用 present_files 展示下载到本地的视频文件。

注意：训练素材必须是无内嵌账号密码的绝对 HTTP(S) URL 且上游可访问；同一账户同类训练进行中时不要重复提交。

## 时长预估标定（实测）

`videoDurationMilliseconds` 与实际文本的关系，实测三组样本：

| 文本类型 | 字数 | 实际时长 | 实际语速 |
| --- | --- | --- | --- |
| 真实中文播报（含标点） | 175 | 33.68 s | 5.20 字/秒 |
| 连续重复字（极端下限） | 400 | 128.72 s | 3.11 字/秒 |
| 连续重复字（极端下限） | 3000 | 967.16 s | 3.10 字/秒 |

结论：**不要用「字数 ÷ 3」这种粗估去卡额度**。若要预扣，按 3 字/秒（实测最慢）计算才安全；正常文本会明显偏保守，多余部分必须退还。真正准确的时长只有 `videoDurationMilliseconds` 说了算，结算一律以它为准。

