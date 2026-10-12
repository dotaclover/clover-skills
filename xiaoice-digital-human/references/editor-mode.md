# 编辑器模式：完整功能清单

普通播报只用 `virtualHuman` + `tts` + `voiceTexts`。但 `scenes[]` 实际是一个**完整的视频编辑器场景**，下面是全部可用字段（**空场景 = 需要至少一个非空场景**）。

版式实测与逐像素踩坑记录见 `layout-pitfalls.md`。

---

## 场景字段总表（`OpenApiScene`）

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
| `backgroundImage` | object | 否 | 场景背景图（自动拉伸覆盖全屏），为空则填白。**⚠️ 实测行为与文档不符，见 `dialogue-video.md`** |
| `backgroundMusic` | object | 否 | 场景背景音乐，**存在全局背景音乐时此项失效** |
| `transferEffects` | object[] | 否 | 转场动画，`{type, duration}` 均必填 |

## 顶层与全局

| 字段 | 说明 |
| --- | --- |
| `outputVideoName` | **必填**，≤100 字 |
| `outputVideoFormat` | 枚举 `mp4` / `mkv`，默认 `mp4`，必须小写 |
| `width` / `height` | 输出画布，默认 `1920` / `1080`；约束 `width * height <= 3840 * 2160` **且必须为偶数** |
| `aigcWatermark` | AI 水印标识，默认 `false` |
| `creationDetail.backgroundMusic` | **全局**背景音乐，设置后所有场景内 `backgroundMusic` 全部失效 |

`OpenApiBackgroundMusic`：`mediaUrl`（必填）、`volume`（0–1，float，1=原始音量）、`speed`（0–3，float）、`loop`（默认 `true`）。

## 虚拟人（`OpenApiVirtualHuman`）

`virtualHumanId`（来自 `detailDigitalEmployee`）、`virtualHumanPostureId`（姿态 `bizId`，必填）、`zIndex`（必填，1–100）、`attributes`（必填）。

`attributes` 四字段 `width` / `height` / `x` / `y` 全必填。**⚠️ 宽高必须与所选姿态的 `previewPicture` 保持原始宽高比，否则虚拟人会被拉伸变形**（换算公式见 `endpoints.md` 的「画布适配」）。

> 想让虚拟人「不出镜」：把 `x`/`y` 移到画布外，或用图层遮挡。

## 图层规则（所有素材共用）

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

## TTS（`OpenApiTts`）

| 字段 | 必填 | 取值 |
| --- | --- | --- |
| `voiceId` | 是 | `detailDigitalEmployee` 的 `VoiceInfo.voiceId` |
| `rate` | 否 | 语速，默认 `1`，**0.6 ≤ rate ≤ 1.5** |
| `pitch` | 否 | 语调，默认 `1`，**0.6 ≤ pitch ≤ 1.5** |
| `volume` | 否 | 音量，默认 `50`，**0 ≤ volume ≤ 100** |
| `latexStyle` | 否 | 公式样式，见下 |

## 自定义音频驱动（替代 TTS）

`scenes[].voiceUrl` 给一个音频 URL（MP3/WAV，≤100MB）即可用现成音频驱动虚拟人。

- 与 `tts` **二选一**。
- **音频时长直接决定场景时长**（不是文本长度）。
- ⚠️ **选用自定义音频后，自动字幕（`caption`）会失效。**

## 字幕（`OpenApiCaption`）

```json
"caption": { "zIndex": 60 }
```

`zIndex` 必填。`topLeft` / `topCenter` / `topRight` 三选一，**全 `false` 时默认居中**。`attributes` 复用 `OpenApiDisplayTextAttributes`。

- 组件宽度自动计算为 **17 个字（含字间距）**，单位像素 —— 宽度会影响居中/居左/居右的实际效果。
- 不填 `attributes` 时：画面居中，y 轴底部留白 1 倍字号，字体默认 6（微软雅黑），字间距 0，字号 40px。

> ⚠️ 上述「不填 `attributes` 的默认行为」**与实测不符** —— 实测成片里字幕完全不出现，必须 `topLeft: true` 且显式传 `x`、`y`。见 `layout-pitfalls.md`。

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

## 文字素材（`OpenApiDisplayText`）

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

## 文字/字幕属性（`OpenApiDisplayTextAttributes`）

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `x` / `y` | 是* | 原点左上角；*作 `caption.attributes` 时非必填（自动居中 / 默认底部留白一号字高） |
| `font` | 是 | 字体序号 1–112，见 `endpoints.md` 的「字体枚举」 |
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

## 图片素材（`OpenApiDisplayImage`）

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `mediaUrl` | 是 | JPG/PNG/GIF，≤10MB。**只接受小冰自家 CDN 域名，见 `assets-and-timing.md`** |
| `zIndex` | 是 | 1–100，不重复 |
| `attributes` | 是 | `width`、`height`、`x`、`y` 全必填；`opacity`（0–1，默认 1）、`rotation`（`0`/`90`/`180`/`270`，默认 0）可选 |

`x`/`y` 不设置时元素处于**画面正中心**。

## 视频素材（`OpenApiDisplayVideo`）

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `mediaUrl` | 是 | MP4，≤300MB |
| `zIndex` | 是 | 1–100，不重复 |
| `attributes` | 是 | 见下 |
| `coverUrl` | 否 | 封面图 url |

`OpenApiDisplayVideoAttributes`：`width` / `height` / `x` / `y`（必填，非等比缩放结果须 > 10）、`durationMilliseconds`（**文档标注为必填**：老引擎依赖，官方说下个版本会修复、不再必填 —— 当前建议照传）、`volume`（0–1）、`loop`。

⚠️ **视频素材无法自动截断，会按顺序依次播放完**，规划时长时要计入。

## LaTeX 公式

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
