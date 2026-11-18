# Seedance 提示词编写参考（最匹配 Seedance 系列）

> 适用范围：Seedance 1.0 / 2.0 / 2.5 全系列。不同版本在镜头控制、多镜头、音频、首尾帧衔接上能力略有差异，但提示词底层公式一致。本参考聚焦于「让提示词最匹配 Seedance」的写法。

## 一、核心公式

```
主体(anchor phrase) + 动作(Motion 清单) + 场景 + 镜头语言 + 光线氛围 + 风格 + 质量/防变形约束
```

Seedance 对「镜头语言」与「运动」响应极强，对抽象形容词响应极弱。因此提示词的价值密度应集中在：**谁、做什么动作、怎么动、怎么拍、什么光、什么风格**。

### 推荐写法（单镜）

> A young woman in a cream knit sweater with long black hair in a low ponytail, holding a silver locket [主体/anchor], turns slowly to face the window [动作], in a dimly lit bedroom at dawn [场景]. Motion: subtle handheld drift, hair shifts, fingers fidget with the locket [Motion 清单]. Medium close-up, slow push-in [镜头语言]. Soft cool morning light through blinds [光线]. Cinematic film grain, anamorphic [风格]. high detail, sharp focus, face clearly visible, no deformation, stable framing, no flicker [质量/防变形].

中文主体/动作用中文清晰描述、风格与镜头术语可中英混用；关键风格词用英文（cinematic、anamorphic、film grain）更精准。

## 二、镜头词汇表（Seedance 强响应）

**运动（每镜只选一种）**

| 英文 | 中文 | 备注 |
| --- | --- | --- |
| static | 固定机位 | 不动 |
| slow push-in | 缓慢推近 | 最常用 |
| pull-back | 缓慢拉远 | |
| pan left / right | 左/右摇 | |
| tilt up / down | 上/下摇 | |
| tracking alongside | 平行跟拍 | |
| orbit around subject | 环绕 | |
| crane up / down | 升降 | |
| handheld follow | 手持跟随 | 带轻微晃动更真实 |
| dolly in / out | 轨道推/拉 | |

**景别（标准术语）**

extreme wide（大远景）→ wide（远景）→ medium（中景）→ medium close-up（中近景）→ close-up（特写）→ extreme close-up（大特写）；另含 over-the-shoulder（过肩）、POV（主观）、aerial（航拍）、insert（插入）。

**速度/节奏词**：slow、smooth、gradual、sudden、brisk、real time、slow motion。

## 三、Motion 清单（最高杠杆的一条）

显式写出 `Motion:` 后接运动节拍，是控制「什么在动、怎么动」最有效的方法。小幅度动作读起来更真实：

- 人物：`subtle handheld drift, hair shifts, fingers fidget, micro pose adjust, breathes gently`
- 环境：`steam rises, fabric sways, dust motes drift, wind in branches, rain on glass`
- 产品：`lid opens smoothly, liquid pours, surface catches a highlight`

> 省略 Motion 清单，模型可能自行发明你并不想要的运镜（如突兀 zoom）。

## 四、Anchor phrase 与一致性

连贯性来自**重复**，而非每次都加新描述。为反复出现的角色构建 anchor phrase，仅包含必须贯穿始终的最小身份要素：

```
角色名/特征 + 服装颜色 + 发型 + 核心道具 + 面向方向
```

- 该短语**逐字复制**到每一处分镜。
- 切勿用近义词替换（"锈红大衣" ≠ "深橙夹克"，会触发视觉重新生成）。
- 建议维护「连续性对照表」：身份 / 服装 / 道具 / 画面朝向 / 布光，生成前逐项比对。

## 五、质量与防变形约束词

末尾固定追加，显著降低变脸/畸形/闪烁：

`high detail, sharp focus, face clearly visible, facial features stable, no deformation, correct human anatomy, natural body proportions, stable framing, no flicker, no morphing`

中文等价：`细节清晰、焦点锐利，面部清晰，五官稳定无畸形，人体结构正常比例自然，画面稳定无闪烁无重影`。

**不要写 `4K` / `8K`。** 分辨率由 `resolution` 参数控制，且只有 Seedance 2.0 标准版支持 4K，2.0 Fast / Mini / 2.5 最高 720p。在提示词里堆 4K 不会提高输出规格，只会让提示词和实际参数对不上。

## 六、多镜头与转场

- 单条提示词只描述**一个连续时刻**；场景切换 = 分开生成。
- 单条时长按型号取：2.0 系列（含 Fast / Mini）4–15s，2.5 为 4–30s 或 `-1`。下限 4s，短于此要并镜。**15s 是技术上限，不是节奏建议。**
- **默认不写提示词内转场标记。** `lens switch` / `cut to` 属于 1.0 时代（Pro / Lite）的流传写法，现行 2.0 / 2.5 没有这两个型号，官方文档也未列出该用法。旧素材里出现时只能标为未验证技巧，不进交付说明。
- 长内容用首尾帧衔接：取上一镜尾帧作下一镜首帧（I2V），衔接点避免运动模糊/快速形变。

## 七、图生视频（I2V）要点

- 提示词描述**运动与变化**，不要重复描述画面里已存在的内容（模型已「看见」参考图）。
- 用小幅、可信的运动，避免极端形变。
- 首帧需精确呈现特定面容/产品/布景时，使用定妆参考图作为首帧。
- 输入图尽量 ≥720p；画幅不匹配时模型中心裁切。

## 八、三视图定妆参考（角色一致性核心）

为核心角色各出**正面 / 侧面 / 背面**三视图定妆图提示词，用于 Seedance 文生图/图生图生成角色参考，再作为 I2V 首帧复用。

**模板（以角色「林晚」为例）：**

```
正面：Character turnaround sheet, front view of [anchor phrase], full body,
standing neutral pose, plain neutral grey background, soft studio light,
clean commercial style, high detail, sharp focus, highly detailed, no text, no logo.

侧面：Character turnaround sheet, side (profile) view of [anchor phrase],
full body, standing neutral pose, plain neutral grey background,
soft studio light, clean commercial style, high detail, sharp focus, highly detailed, no text.

背面：Character turnaround sheet, back view of [anchor phrase], full body,
standing neutral pose, plain neutral grey background, soft studio light,
clean commercial style, high detail, sharp focus, highly detailed, no text.
```

- 三视图共用同一 anchor phrase，确保颜色/发型/道具完全一致。
- 若用户偏好 3D 皮克斯风，可在风格位替换为 `Pixar-style 3D render, three-quarter lighting`，但三视图仍建议先出写实/设定稿再转风格，避免风格化干扰一致性比对。

## 九、短剧专项

- **节奏钩子**：前三秒用「视觉动词」做 Hook（倒入、打开、旋转、揭示、滑过、咔哒合上），不要写概念词（"表现好奇心"）。
- **音频连续性**：每个分镜填「音效/对白」栏；跨镜衔接处标记是否会打断角色对白，若存在打断点需调整剪辑或重新分配台词。
- **成本提示**：每镜标注预估（如「需 I2V 首帧 + 主生成，约 2 次渲染」「可用草稿 480p 预览后再出正片」）。

## 十、常见错误（务必避免）

1. 抽象形容词堆砌："stunning, cinematic, ultra-realistic, 8K masterpiece"——不指向任何可见内容。
2. 负向提示词："no blurry hands"——Seedance 不按预期工作，改描述想要的样子。
3. 矛盾要求："frozen in time while running fast"——只能取其一。
4. 一条提示词塞三个场景——一个 prompt 一个连续时刻，场景切换分开生成。
5. 单镜堆叠多个运动（"pan then zoom then crane"）——4–15s 只承载一个镜头想法。
6. 长篇小说式提示词——字数过长会稀释前面细节；5 个信息密集句胜过 20 句模糊句。
7. anchor phrase 用近义词替换——触发视觉重新生成，破坏一致性。
