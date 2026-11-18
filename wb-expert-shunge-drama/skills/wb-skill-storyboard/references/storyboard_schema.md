# 分镜 spec JSON 字段定义与示例

> `scripts/build_storyboard.py` 读取此结构的 JSON，产出 Markdown 分镜表 + 规范化 JSON + Excel 分镜表（缺 `openpyxl` 时自动安装；可用 `--no-excel` 跳过）。
> 下表为字段定义；其后附一段可直接改写的完整示例（短剧开场 3 镜）。

## 字段定义

### meta（对象，必填 title）
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| title | string | 分镜表标题 |
| genre | string | 类型，默认「短剧/剧情」 |
| model_family | string | 目标型号，填 Model ID 或 `2.0`/`2.0-fast`/`2.0-mini`/`2.5`；决定单镜时长上限与可用分辨率 |
| aspect_ratio | string | 画幅，默认「9:16」 |
| resolution | string | 分辨率，默认「720p」。1080p/4K 仅 2.0 标准版可用，Fast/Mini/2.5 最高 720p |
| total_duration_sec | number | 总时长（秒） |
| notes | string | 总备注 |

### characters[]（数组，至少 1 个核心角色）
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | string | 角色标识，如 `char_1` |
| name | string | 角色名 |
| anchor_phrase | string | **逐镜复用的固定身份短语**（服装/发型/道具/肤色/体型） |
| appearance | string | 外观要点补充（可选） |
| three_view.front / side / back | string | 正面/侧面/背面定妆图提示词（Seedance 文生图/图生图用） |
| three_view_zh.front / side / back | string | （可选）中文版三视图定妆图提示词；`--pure-zh` 纯中文导出时优先使用，缺失则回退 `three_view` |

### shots[]（数组，至少 1 镜）
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| shot_id | number/string | 镜号 |
| duration_sec | number | 单镜时长，4s 起；上限按 `model_family`：2.0 系列 15，2.5 为 30 |
| timecode | string | 时间码，如 `00:00-00:05` |
| beat | string | 戏剧节拍：钩子/铺垫/冲突/反转/高潮/结局 |
| visual | string | 中文画面描述 |
| anchor | string | 本镜主体（通常复用某角色 anchor_phrase） |
| motion | string | `Motion:` 运动清单 |
| camera | string | 景别 + 单一运动 |
| lighting | string | 光线氛围 |
| style | string | 风格 |
| quality | string | 质量/防变形约束 |
| prompt | string | **最终合并的 Seedance 提示词**（必填，可直接复制）。若留空，脚本会按公式 `anchor + motion + camera + lighting + style + quality` 自动拼装；已填则优先使用手填值 |
| prompt_zh | string | （可选）中文版最终提示词；存在时 Markdown/Excel 会同时渲染中英文两版，`--pure-zh` 纯中文导出时作为其唯一提示词 |
| ivf_first_frame | string | I2V 首帧来源，如「使用 char_1 正面定妆图」「使用镜 1 尾帧」 |
| audio | string | 音效/对白（用户强关注音频连续性） |
| cost_note | string | 成本/备注提示 |

## 自动补全与自检（v1.2.0 起）

`scripts/build_storyboard.py` 在生成前会自动增强 spec，并在控制台输出自检报告：

- **提示词自动拼装**：分镜缺 `prompt` 时，按公式从 `anchor / motion / camera / lighting / style / quality` 拼出 Seedance 提示词；手填 `prompt` 优先。
- **三视图自动生成**：角色缺 `three_view` 时，按 `anchor_phrase` 自动生成 正面/侧面/背面 三视图定妆提示词；手填则保留。
- **一致性自检（告警不阻断生成）**：
  - 每镜 `anchor` 是否与某角色 `anchor_phrase` **逐字相等**（不一致会触发 Seedance 视觉重新生成）；
  - 单镜 `duration_sec` 是否不超过 `model_family` 对应的上限（2.0 系列 15s、2.5 为 30s；缺省按 2.0 系列），以及是否短于 4s 下限；
  - `camera` 字段是否只含**一种**镜头运动；
  - 是否缺失 `audio` / `cost_note` / `prompt_zh`。
- **命令行开关**：`--no-auto` 关闭上述自动补全（完全按手填输出）；`--check` 只跑校验与自检报告、不写任何文件（适合交付前体检 / CI）。

> 注：示例 JSON 已手填 `prompt` 与 `three_view`，因此运行后「自动补全」项为 0，输出与旧版一致——新能力在「精简 spec（只填结构化字段）」时生效。

## 完整示例（可直接改写）

```json
{
  "meta": {
    "title": "《鸠占鹊巢》开场分镜",
    "genre": "短剧/剧情",
    "model_family": "doubao-seedance-2-0-260128",
    "aspect_ratio": "9:16",
    "resolution": "720p",
    "total_duration_sec": 25,
    "notes": "女主归来复仇开场，强调冷感与克制；角色一致性优先。"
  },
  "characters": [
    {
      "id": "char_1",
      "name": "林晚",
      "anchor_phrase": "a slender woman in a fitted charcoal trench coat with long straight black hair and a sharp fringe, carrying a worn leather satchel",
      "appearance": "冷白皮，眉眼凌厉，左耳一枚银坠；23 岁质感",
      "three_view": {
        "front": "Character turnaround sheet, front view of a slender woman in a fitted charcoal trench coat with long straight black hair and a sharp fringe, carrying a worn leather satchel, full body, neutral standing pose, plain neutral grey background, soft studio light, clean commercial style, high detail, sharp focus, no text, no logo.",
        "side": "Character turnaround sheet, side profile view of a slender woman in a fitted charcoal trench coat with long straight black hair and a sharp fringe, carrying a worn leather satchel, full body, neutral standing pose, plain neutral grey background, soft studio light, clean commercial style, high detail, sharp focus, no text, no logo.",
        "back": "Character turnaround sheet, back view of a slender woman in a fitted charcoal trench coat with long straight black hair and a sharp fringe, carrying a worn leather satchel, full body, neutral standing pose, plain neutral grey background, soft studio light, clean commercial style, high detail, sharp focus, no text, no logo."
      }
    }
  ],
  "shots": [
    {
      "shot_id": 1,
      "duration_sec": 5,
      "timecode": "00:00-00:05",
      "beat": "钩子",
      "visual": "雨夜豪宅铁门，一只手将一封烫金请柬塞进门缝，雨水打湿信封。",
      "anchor": "a slender woman in a fitted charcoal trench coat with long straight black hair and a sharp fringe, carrying a worn leather satchel",
      "motion": "Motion: rain streaks down the iron gate, fingers release the envelope, water droplets slide off the gold edge.",
      "camera": "Extreme close-up, static",
      "lighting": "cold blue streetlight, wet reflections",
      "style": "cinematic, anamorphic flare, film grain",
      "quality": "high detail, sharp focus, stable framing, no flicker, no deformation",
      "prompt": "Extreme close-up of an iron estate gate at night in the rain, a slender woman's hand in a fitted charcoal trench coat sleeve slips a gold-embossed invitation through the gap, rain streaks down the metal, water droplets slide off the gold edge. Motion: rain streaks down the iron gate, fingers release the envelope, water droplets slide off the gold edge. Static camera. Cold blue streetlight, wet reflections. Cinematic, anamorphic flare, film grain. high detail, sharp focus, stable framing, no flicker, no deformation.",
      "ivf_first_frame": "使用女主手部特写定妆参考（char_1 局部）",
      "audio": "对白：无；音效：雨声、信封落地的轻响",
      "cost_note": "文生视频即可；建议 480p 草稿确认构图后再出正片。"
    },
    {
      "shot_id": 2,
      "duration_sec": 10,
      "timecode": "00:05-00:15",
      "beat": "铺垫",
      "visual": "林晚立于门内阴影，缓缓抬头，目光冷冽扫过厅堂。",
      "anchor": "a slender woman in a fitted charcoal trench coat with long straight black hair and a sharp fringe, carrying a worn leather satchel",
      "motion": "Motion: subtle head rise, fringe shifts, eyes scan the room, coat hem settles.",
      "camera": "Medium shot, slow push-in",
      "lighting": "dim warm chandelier glow against cool shadow",
      "style": "cinematic, shallow depth of field, film grain",
      "quality": "high detail, sharp focus, face clearly visible, facial features stable, no deformation, stable framing, no flicker",
      "prompt": "A slender woman in a fitted charcoal trench coat with long straight black hair and a sharp fringe, carrying a worn leather satchel stands in the shadow just inside the gate, slowly raises her head, her cold gaze sweeps across the lavish hall. Motion: subtle head rise, fringe shifts, eyes scan the room, coat hem settles. Medium shot, slow push-in. Dim warm chandelier glow against cool shadow. Cinematic, shallow depth of field, film grain. high detail, sharp focus, face clearly visible, facial features stable, no deformation, stable framing, no flicker.",
      "ivf_first_frame": "使用 char_1 正面定妆图",
      "audio": "对白：（内心独白）「这宅子，我回来了。」；音效：远处留声机杂音",
      "cost_note": "需 I2V 首帧（定妆图）+ 主生成，约 2 次渲染；角色一致性关键镜。"
    },
    {
      "shot_id": 3,
      "duration_sec": 10,
      "timecode": "00:15-00:25",
      "beat": "冲突",
      "visual": "林晚抬手摘下湿外套，露出内里暗红丝缎，旋身走向楼梯，镜头平行跟拍。",
      "anchor": "a slender woman in a fitted charcoal trench coat with long straight black hair and a sharp fringe, carrying a worn leather satchel",
      "motion": "Motion: removes the coat in one smooth motion, deep red silk lining revealed, turns and strides toward the staircase, satchel swings.",
      "camera": "Tracking alongside, steady",
      "lighting": "warm chandelier now dominant, long shadows",
      "style": "cinematic, anamorphic, film grain",
      "quality": "high detail, sharp focus, body proportions natural, no deformation, stable framing, no flicker",
      "prompt": "A slender woman in a fitted charcoal trench coat with long straight black hair and a sharp fringe, carrying a worn leather satchel removes the coat in one smooth motion to reveal deep red silk lining, turns and strides toward the staircase, the satchel swinging at her side. Motion: removes the coat in one smooth motion, deep red silk lining revealed, turns and strides toward the staircase, satchel swings. Tracking alongside, steady. Warm chandelier now dominant, long shadows. Cinematic, anamorphic, film grain. high detail, sharp focus, body proportions natural, no deformation, stable framing, no flicker.",
      "ivf_first_frame": "使用镜 2 尾帧（林晚抬头姿态）衔接，避免姿态跳变",
      "audio": "对白：无；音效：高跟鞋叩地、衣料摩擦",
      "cost_note": "衔接镜：用镜 2 尾帧作首帧，衔接点勿用运动模糊，保证姿态连续。"
    }
  ]
}
```
