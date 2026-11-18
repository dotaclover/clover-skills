---
name: wb-skill-storyboard
display_name: seedance分镜专家顺哥
display_name_en: Seedance Storyboard Expert Shunge
description: 将短剧/剧情类文案转换为分镜表，并为 Seedance 2.0 / 2.5 系列生成匹配的提示词——含人物三视图定妆参考与图生视频(I2V)首帧方案，输出 Markdown 分镜表、JSON 与 Excel。触发词：分镜、分镜表、拆镜头、Seedance、即梦、豆包视频、短剧分镜、镜头脚本、三视图定妆、角色一致性、首帧、I2V、提示词。
description_zh: 把短剧或剧情文案拆成可直接生成的分镜表，为每个镜头写 Seedance 2.0 / 2.5 提示词：固定 anchor phrase 保角色一致、显式 Motion 清单、单镜单运动、I2V 首帧方案、三视图定妆提示词，附型号时长与分辨率边界校验。输出 Markdown 分镜表、JSON 与 Excel 三格式。当用户要做分镜、拆镜头、写生成提示词、保证角色跨镜一致时使用。
description_en: Turn short-drama or plot copy into generation-ready storyboards with per-shot Seedance 2.0 / 2.5 prompts - fixed anchor phrases for character consistency, explicit motion lists, one camera move per shot, I2V first-frame plans, and turnaround reference prompts, with model-aware duration and resolution checks. Outputs Markdown, JSON, and Excel. Use when a user asks for a storyboard, shot breakdown, Seedance prompts, or cross-shot character consistency.
version: "1.0.0"
license: proprietary
allowed-tools: Read, Write, Bash
metadata:
  author: clover
  category: content-marketing
  tags: [分镜, 短剧, Seedance, 提示词, 角色一致性, 图生视频]
agent_created: true
---

# seedance分镜专家顺哥

## 使用边界

本技能只做分镜与提示词，不提交生成、不代付费用。分镜确认后，生成走 `seedance-dev`（Ark / 百度 / 华锐渠道）或网页版渠道；两边参数口径不同，本表字段不能直接当接口参数照搬。

## Overview

把一段短剧/剧情类文案，转化为可直接送进 Seedance 系列视频模型生成的分镜交付物：每个镜头配一条按 Seedance 提示词公式写就的提示词、一套人物三视图定妆参考（供 I2V 首帧复用）、以及 **Markdown 分镜表 + JSON + Excel 三格式**产物。核心目标是「提示词最匹配 Seedance」——遵循其镜头语言强响应、单镜头单运动、anchor phrase 一致性、显式 Motion 清单、防变形约束等特性。

## 何时使用

- 用户给一段文案/剧本，要求「拆分镜」「做分镜表」「出 Seedance 提示词」。
- 用户做短剧二创、剧情短片，需要角色跨镜头一致性方案与定妆参考。
- 用户需要把分镜导出为 JSON 接入生成流水线，同时保留可读的分镜表。

## 工作流

严格按以下顺序执行：

### 1. 解析文案与戏剧结构

- 识别文案类型（本 skill 面向短剧/剧情类）。
- 提取戏剧节拍：**钩子 → 铺垫 → 冲突 → 反转 → 高潮 → 结局**。
- 估算总时长与目标节奏；确定画幅（默认 9:16 竖屏）、目标型号与分辨率（见下表，**不要默认 1080p**）。

### 2. 先锁型号参数（决定后面所有拆分）

不同型号的时长与分辨率不通用，先问清用哪个 model，再拆镜。写成 `meta.model_family`。

| 型号 | Model ID | 分辨率 | 单条时长 |
|---|---|---|---|
| Seedance 2.5 | `doubao-seedance-2-5-260628` | 480p / 720p | 4–30s，或 `-1` 由模型决定 |
| Seedance 2.0 | `doubao-seedance-2-0-260128` | 480p / 720p / 1080p / 4K(10bit) | 4–15s |
| Seedance 2.0 Fast | `doubao-seedance-2-0-fast-260128` | 480p / 720p | 4–15s |
| Seedance 2.0 Mini | `doubao-seedance-2-0-mini-260615` | 480p / 720p | 4–15s |

- **1080p 与 4K 只有 2.0 标准版支持**；2.5、Fast、Mini 最高 720p。默认按 720p 拆，客户明确要高清再确认型号。
- 下限 4s：短于 4s 的镜头不能单独生成，要并镜或改用其他手段。
- `duration: -1` 仅 2.5 与编辑/延长任务可用，2.0 系列必须给整数。
- 参考素材上限同样分型号：2.0 系列参考图 1–9 张、参考视频 ≤3 个总时长 ≤15s；2.5 参考图最多 30 张、参考视频 ≤10 个合计 ≤30s。2.0 系列**不能只给音频**做唯一参考。

参数事实源：`seedance-dev/references/legacy-seedance-video.md`（官方历史实测表）与 `ark-api.md`。本节参数如与上游渠道资料冲突，以上游当前文档为准。

### 3. 拆分分镜

- 按戏剧节拍拆成镜头；单镜时长 **4s 起，建议 5–10s**，上限按型号取（2.0 系列 15s，2.5 为 30s）。超上限才切镜或首尾帧衔接。
- **15s 不是节奏建议，是技术上限**。故事密度该切就切，别为了用满 15s 把一个镜头拖长。
- 为每个镜头标注：镜号、时长、时间码、节拍、画面描述。

### 4. 为每个分镜写 Seedance 提示词

套用公式（详见 `references/seedance_prompt_guide.md`）：

```
主体(anchor phrase) + 动作(Motion 清单) + 场景 + 镜头语言 + 光线氛围 + 风格 + 质量/防变形约束
```

关键规则：

- 主体用固定 **anchor phrase**，且逐镜**逐字复用**同一措辞（见一致性）。
- 动作写成可见动词 + 显式 `Motion:` 清单（如 `Motion: subtle handheld drift, hair shifts, fingers fidget`）。
- 镜头语言：单镜头只选**一种**运动（push-in / pull-back / pan / orbit / tracking / crane / handheld / static），配标准景别（extreme wide → extreme close-up）。
- 避免抽象形容词堆砌（"stunning, cinematic, 8K masterpiece" 无效），每个词都要指向可见/可听内容。
- 不加负向提示词（"no blurry hands" 无效），改描述想要的样子。
- 末尾加质量与防变形约束：`high detail, sharp focus, face clearly visible, no deformation, stable framing, no flicker`。
- **不要写 `4K` / `8K`**：只有 2.0 标准版支持 4K，其余型号最高 720p。约束词里写死分辨率不会提画质，只会让提示词与输出规格脱节。真要 4K，改的是 `resolution` 参数不是提示词。

### 5. 运镜与转场 / 衔接

- **一个镜头一条提示词、一种运动**。场景切换一律拆成两个镜头分开生成，不靠提示词里的转场词硬切。
- `lens switch` / `cut to` 这类转场标记是 1.0 时代（Pro/Lite）的写法，现行 2.0/2.5 没有 Pro/Lite 型号，官方文档也未列出这类标记。**要保留旧素材时只能当作未验证技巧**，不能写进交付说明当承诺；默认不写。
- 衔接处：把上一镜**尾帧**作为下一镜**首帧**（I2V），并在该分镜标注 `ivf_first_frame` 来源；衔接点避免运动模糊/快速形变。用首尾帧时 `ratio` 强制 `adaptive`。
- 一条提示词只描述一个连续时刻；场景切换 = 分开生成。

### 6. 生成人物三视图定妆参考

- 为核心角色各出**正面/侧面/背面**三视图定妆图提示词（Seedance 文生图/图生图），锁定：服装颜色、发型、核心道具、肤色、体型、年龄感。
- 三视图提示词写入 `characters[].three_view`，并在角色出场/关键分镜的 `ivf_first_frame` 中引用对应视图，保证跨镜头一致性。
- 定妆提示词模板见 `references/seedance_prompt_guide.md` 的「三视图定妆」。

### 7. 产出三格式

- 先写出 spec JSON（见 `references/storyboard_schema.md` 的字段定义与示例）。**不必手抄 `prompt` 与 `three_view`**——脚本会自动拼装（见下）。
- 运行脚本一次性生成 **Markdown 分镜表 + 规范化 JSON + Excel 分镜表**：

  ```bash
  python scripts/build_storyboard.py --input <spec.json> --out-dir <dir>
  ```

  - **提示词自动拼装**：spec 中某分镜缺 `prompt` 时，脚本按公式 `anchor + motion + camera + lighting + style + quality` 自动拼出 Seedance 提示词；已手填 `prompt` 的镜优先用手填值。
  - **三视图自动生成**：角色缺 `three_view` 时，脚本按 `anchor_phrase` 自动生成 正面/侧面/背面 三视图定妆提示词；已手填则保留。
  - **一致性自检**：脚本自动核对 `anchor` 逐字一致、单镜时长不超型号上限、单镜头单运动、关键字段（audio/cost_note/prompt_zh）是否缺失，并在控制台输出报告（告警不阻断生成）。上限由 `meta.model_family` 决定，缺省按 2.0 系列 15s。
  - Excel 含三张 sheet：**总览 / 人物定妆 / 分镜表**，表头带样式、自动换行、冻结首行、可筛选，便于直接在表格里审阅与批量填字。
  - 若无需 Excel，加 `--no-excel` 跳过；脚本会自动安装 `openpyxl`（缺失时）。
- **中文提示词（可选）**：每个分镜可在 spec 中加 `prompt_zh`（中文最终提示词）。存在时，Markdown 与 Excel 会同时渲染「英文提示词 + 中文提示词」两栏/两区块，方便中文团队直接复制使用。
- **纯中文导出（可选）**：运行脚本时加 `--pure-zh`，会额外产出 `<name>_纯中文.md` 与 `<name>_纯中文.xlsx`——所有可读内容与最终提示词均为中文，镜头/光线/风格/质量字段亦译为中文；人物三视图定妆使用角色 `three_view_zh`（缺失则回退英文）。注意：角色 `anchor phrase` 作为模型固定身份令牌保持英文原样（跨镜一致性依赖它），并在「人物定妆」区注明，请勿翻译或改写。
- **仅自检（可选）**：加 `--check` 只跑校验与一致性报告、不写任何文件，适合交付前快速体检或接入 CI。加 `--no-auto` 可关闭自动补全、完全按手填内容输出。
- 若脚本校验报错，按提示修正 spec 后重跑。

### 8. 自检清单（交付前必过）

> 以下前四项已由 `build_storyboard.py` 在生成时**程序化核对**（控制台输出报告），手填 spec 时可重点看报告告警。

- [ ] 每个角色的 anchor phrase 在所有分镜中**逐字一致**（近义词也会触发重新生成）。
- [ ] 单镜头仅一种镜头运动；多镜头已拆成独立镜头生成，无提示词内转场标记。
- [ ] 无抽象形容词堆砌、无负向提示词、无矛盾要求（如「超高速 + 极致稳定」）、无 `4K`/`8K` 分辨率词。
- [ ] 时长分配合理：每镜 4s 起，且不超目标型号上限（2.0 系列 15s / 2.5 为 30s）。
- [ ] 分辨率与目标型号匹配（1080p 或 4K 仅在 2.0 标准版成立）。
- [ ] 含人物三视图定妆；关键分镜标注了 I2V 首帧来源。
- [ ] 音频/对白栏已填，且跨镜衔接处**无打断角色对白的剪辑点**（用户强关注项）。
- [ ] 每镜含成本/备注提示。

## 资源

- `references/seedance_prompt_guide.md` — Seedance 提示词公式、镜头词汇表、景别、Motion 清单、anchor phrase、防变形、多镜头转场、I2V、三视图定妆模板。
- `references/storyboard_schema.md` — spec JSON 字段定义 + 完整示例（可直接改写的模板）。
- `scripts/build_storyboard.py` — 由 spec JSON 生成 Markdown 分镜表、规范化 JSON 与 Excel 分镜表（依赖 `openpyxl`，缺失时自动安装）。支持 `prompt` 与 `three_view` 自动补全、`--pure-zh` 纯中文导出、`--check` 一致性自检（不写文件）、`--no-auto` 关闭自动补全。
