# 视频生成核心接口

覆盖：查询形象 → 形象详情 → 提交任务 → 轮询 → 任务管理 → 素材枚举 → 画布适配。

---

## 1. 查询形象（数字员工）

```json
POST /openapi/video/queryDigitalEmployee
{ "categoryList": [0], "modelType": "STUDIO", "pageIndex": 1, "pageSize": 100 }
```

返回 `data: {records: [{bizId, name, category, summaryImage, summaryVideo}], total, pages}`。`categoryList: [0]` 为官方公共形象；分页取完所有页，总数以 `total` 为准。

## 2. 形象详情（获取 virtualHumanId 与可选声音/姿态）

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

## 3. 提交视频任务

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

## 4. 轮询任务

```json
GET /openapi/video/task/v2/detail?taskId=<任务ID>
```

`data` 字段：`status`、`progress`（0–1 小数）、`videoUrl`、`videoThumbnailImageUrl`、`videoDurationMilliseconds`、`videoSizeBytes`、`error`、`createTime`、`finishTime`、`clientType`。

- **`status` 枚举：官方文档为 `running`（创建中）/ `finished`（完成）/ `error`（失败）**。历史版本和不同接口出现过 `queued`/`processing`/`failed`，判断时要做宽松匹配（大小写、空白也归一化）。**只判断 `failed` 会漏掉 `error`，导致失败任务永远停在「进行中」、预扣额度不退。**
- `finished` 才有 `videoUrl`，立即下载转存，不要把 URL 当长期地址。
- 失败时看 `data.error` 或 `message`。
- 计费按实际时长：`ceil(videoDurationMilliseconds / 1000)` 秒，上限 3600。
- `data` 实测是对象，官方文档标注为数组 —— 两种都要兼容。

## 4.1 删除任务与任务列表（官方文档有，常被忽略）

```json
POST /openapi/video/task/v2/remove
{ "taskIds": ["<任务ID>", "<任务ID>"] }     // 批量删除，返回 code 200

POST /openapi/video/task/v2/pageQuery
{ "pageIndex": 1, "pageSize": 50 }          // 列出企业下全部任务
```

`pageQuery` 可选过滤：`userId` / `userEmail` / `userPhone`（三者只需传一个；都不传则返回企业下所有任务）。

返回 `data` 是 `Page` 对象：`{current, size, total, pages, records[]}`，`records[]` 与轮询接口的 `VideoTaskResult` 同构。**这是对账上游真实用量的唯一途径** —— 把全量 `videoDurationMilliseconds` 求和即可核对实际消耗（比逐任务轮询可靠得多）。

### ⚠️ `remove` 不是「取消任务」（实测结论）

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

## 4.2 视觉素材枚举（写死不如实时拉取）

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

## 4.3 字体枚举（`attributes.font` 用序号）

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

---

## 画布适配（虚拟人宽高比）

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

**不同形象的姿态图尺寸并不一致**（实测形象 `VHPVCW35N3M8DO0` 是 720×1280，形象 `VHPBL0UBK89PAV6` 是 2160×3840），所以**不能写死 1080×1920** —— 这是最容易出的画质问题。
