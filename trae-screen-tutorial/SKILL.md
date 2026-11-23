---
name: trae-screen-tutorial
description: "顺哥教程系列（基于 Trae）专用出片技能：把真实操作录屏与截图做成竖版 9:16、横版 16:9 的短教程（4 拍约 30 秒），统一 WorkBuddy 同款视觉、统一顺哥口播风格，品牌素材随技能打包，即插即用。用户要做顺哥 Trae 教程、AI 编程短课、系列连更时调用。"
agent_created: true
---

# 顺哥教程系列 · 基于 Trae 出片

把「真实操作录屏 + 截图」做成手机上好读的短教程。核心不是把 16:9 压成 9:16，而是**每一拍只讲一件事、只留一个焦点**，用顺哥的口播补上「为什么」。视觉跟 WorkBuddy 讲解台同源：夜景桌面底图、常驻品牌头像、奶油内容卡、WorkBuddy 蓝强调，观众一眼认出是同一个人的系列。

一集 = 4 拍，约 30 秒：`c01 钩子卡 → d1 真机演示 → c02 点破卡 → c99 结束卡`。

## 什么时候用

- 要把一段 Trae 的真实操作（对话生成 / IDE 改代码 / 浏览器看结果）做成短教程。
- 要做「Trae课程100课」这类系列，一集一个知识点，竖版发抖音/视频号，横版发 B 站/公众号。
- 要统一品牌视觉与口播风格、批量连更。

不适用：纯口播、无人值守超长录屏、纯 16:9 长讲座（本技能横版是短横屏，不是长片）。

## 交付形态

```
<系列项目>/
├─ episodes/EPxx/beats.json     # 唯一事实源：每一拍的全部参数
├─ build/
│   ├─ epxx.mp4                  # 竖版 1080×1920
│   ├─ epxx-16x9.mp4             # 横版 1920×1080（同物料同配音）
│   ├─ demo_epxx.mp4             # 剪好的真机演示片段（可选）
│   ├─ audio/                    # TTS 缓存（按文案 sha1）
│   ├─ parts/ parts16/           # 每拍静帧 / 分段
└─ series.json / 排产表.md        # 可选：全局选题与进度
```

## 四拍结构（约 30 秒）

| 拍 | 作用 | 画面 | 时长 |
|---|---|---|---|
| `c01` | 钩子：抛痛点/反常识 | 文字卡（大标题 + 两行 panel + 结论） | 6–7s |
| `d1` | 演示：真机操作，眼见为实 | 全宽录屏片段（video）或截图（img） | 8–14s |
| `c02` | 点破：一句话给结论 | 文字卡 | 6–8s |
| `c99` | 收尾：品牌结束卡 | 头像 + 「搜索添加 / AI从零开始 / 关注我…」 | 5–6s |

时长算法：`dur = 配音时长 + 0.55 + hold`，量化到 1/30 秒；素材比配音长就加速，短就挂尾帧。

## 竖版视觉（build_video.py，已内置）

- 底图：`assets/stage-bg.png`（WorkBuddy 讲解台竖版，1440×2560，缩到 1080×1920）
- 头像：`assets/avatar.jpg`，只在文字卡/结束卡出现；**真机演示页不显示头像**
- 配色：深色字 `(28,34,50)`、奶油卡、WorkBuddy 蓝 `(48,110,190)`
- 口播字幕落底部奶油条；结论字幕在内容卡下沿
- 文字卡带两个小图标点缀（`</>` + 星芒），版面更平衡

素材路径相对技能目录，可用环境变量覆盖：`WB_STAGE_BG`、`WB_AVATAR`。

## beats.json 字段

```json
{
  "tag": "入门基础·EP01",
  "ep": "01",
  "hold": { "c01": 0.4, "d1": 0.4, "c02": 0.4, "c99": 1.0 },
  "beats": [
    { "name": "c01", "kind": "text", "title": "一句钩子",
      "panel": ["大字一", "大字二"], "cap": ["结论一", "结论二"],
      "voice": "钩子口播" },
    { "name": "d1", "kind": "video", "src": "build/demo_ep01.mp4",
      "t_in": 0.0, "t_out": 20.7, "title": "演示标题",
      "cap": ["演示结论"], "voice": "演示口播" },
    { "name": "c02", "kind": "text", "title": "点破标题",
      "panel": ["一句话结论"], "cap": ["补充"], "voice": "点破口播" },
    { "name": "c99", "kind": "text", "endcard": true,
      "title": "结束卡标题",
      "panel": ["搜索添加", "AI从零开始", "关注我，带你用AI从零学编程"],
      "cap": [], "voice": "收尾口播（不念搜索添加/关注我）" }
  ]
}
```

- `kind`：`text`（文字卡）/ `img`（截图，`crop:[路径,x,y,w,h]` 覆盖裁切）/ `video`（`src` + `t_in`/`t_out`）
- `endcard: true` → 走品牌结束卡版式（浅底 + 大头像 + 蓝色大字）
- 素材路径可为绝对路径，或相对 beats.json 所在目录
- 配音：edge-tts，`zh-CN-YunxiNeural`，`+8%`；文本变了会重新生成

## 口播铁律

1. **不许出现「下一条」**：结尾不预告下一集，收在结论上。
2. **「关注我…」只上画面、不口播**；「搜索添加 / AI从零开始」同样只做视觉。
3. **读音雷区**（写文案时避开，TTS 会读错）：
   - 门槛 → 门坎；联调 → 联合调试；命令行 → 终端命令
   - 放手干 → 真放手；怎么干 → 怎么做；干 → 做
   - 例外保留：古法编程、把活干完
4. 标题约 20 字，不标题党、不虚构画面里没有的东西。

## 真机演示怎么录、怎么裁（关键）

- **必须是真实操作**，不能只放结果页。演示要能看到鼠标操作与画面变化。
- 录屏前后把环境弄干净：
  - 用 **app 模式**开页面：`chrome.exe --app=file:///C:/.../hello.html`（无标签栏/地址栏）
  - **不要用带私人标签的浏览器窗口**（会露 OpenAI/API 等隐私）
  - **不要右键**：右键菜单会一直挂在文件树上，整段作废
  - 操作前把目标窗口置前（可用 PowerShell `SetForegroundWindow`），避免点击落到别的窗口
- 出片时统一裁掉：
  - **底部 Windows 任务栏/状态栏**
  - **浏览器标准栏/窗口标题栏**
  - 参考配方见 `references/08-拍摄与裁切.md`

## 命令（在系列项目根目录执行）

```bash
pip install -r requirements.txt                 # Pillow / edge-tts / numpy

# 竖版 1080×1920
python scripts/build_video.py --beats episodes/EP01/beats.json --preview   # 先看静帧
python scripts/build_video.py --beats episodes/EP01/beats.json             # 出 build/ep01.mp4

# 横版 1920×1080（同 beats、同配音）
python scripts/build_landscape.py --beats episodes/EP01/beats.json --preview
python scripts/build_landscape.py --beats episodes/EP01/beats.json          # 出 build/ep01-16x9.mp4
```

依赖 `ffmpeg`/`ffprobe` 在 PATH；中文字体用系统 `msyhbd.ttc`/`msyh.ttc`。

## 验收清单（没抽帧看过不算完成）

- 竖版：文字卡头像在圈内、标题条可读、字幕不压边；真机页无头像、全宽铺满、无任务栏/浏览器栏
- 横版：PPT 页奶油卡通透、真机页满屏、字幕在底部
- 音轨存在、时长≈30s、每拍口播与画面一致
- 结束卡无「下一条」，未口播「关注我/搜索添加」

## 参考索引

| 文档 | 内容 |
|---|---|
| `references/00-顺哥profile.md` | 顺哥人设、表达偏好、竖/横产品线、固定句式 |
| `references/01-流程与分镜.md` | 片长、拍数、叙事模板、时长算法 |
| `references/02-素材与裁切.md` | 录屏/长截图/手机录屏的取景与加速 |
| `references/03-配音与字幕.md` | 音色语速、多音字坑、两层字幕、混音 |
| `references/04-版式与封面.md` | 固定版式坐标、配色、封面模板 |
| `references/05-发布与文案.md` | 抖音规格、文案结构、多平台分发 |
| `references/06-后期与验收.md` | ffmpeg 配方、验收清单、故障对照 |
| `references/07-配置字段.md` | beats.json 全字段 |
| `references/08-拍摄与裁切.md` | 真机演示录制规范 + 隐藏任务栏/浏览器标准栏配方 |
| `references/absorbed/…` | 吸收的抖音脚本、豆包制图、通用后期方法论 |

## 边界

- 只做「已有素材 → 成片」，不自动录屏、不做 ASR、不自动识别场景。
- 不虚构画面里没有的输入、弹窗、报错。
- 不自动上传平台；发布文案给人，由人来发。
- TTS 需联网；离线时用缓存 mp3 或纯字幕版。
