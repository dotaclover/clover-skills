# Clover Skills

这个目录保存可直接被 WorkBuddy（以及 Codex 等支持 Agent Skills 的工具）发现的独立 Skill。每个 Skill 都必须是一个目录，并包含 UTF-8 编码的 `SKILL.md`；较长的流程、平台差异、示例和脚本放在 `references/`、`scripts/` 或 `assets/` 中。

## 推荐的技能边界

### 内容创作

以下技能都遵循“输入简报 → 选题/标题 → 正文或口播 → 封面/配图 → 合规检查”的流程，但保留各平台的独立规则：

- `douyin-script-studio`
- `kuaishou-script-studio`
- `wxchannels-script-studio`
- `xhs-note-studio`
- `wechat-mp-studio`
- `toutiao-article-studio`

不要把六个平台合并成一个无差别的触发入口；平台差异会影响标题、时长、文体、封面和合规检查。

第七个内容技能按**文体**切、不按平台切：

- `versus-script-studio`（对决稿）⚠️ **v0.1 未完成，待完善**

只做 3–4 分钟的双对象横评口播（九段骨架、金句收束、短板双向、结尾不给赢家）。平台侧规则仍回三个口播工坊补，两边正交，不要合并。

> ⚠️ **状态：draft（v0.1）**。可用部分＝九段骨架 / 段落节奏表 / 四条写作规则 / 事实纪律；
> 未完成＝无可执行脚本、案例库只有 1 条、不出拆条与分镜。完成标准见该技能 `SKILL.md` 的待完善清单。

### 视频与数字人

- `seedance-video`：生成新视频、参考素材、编辑/延长、提交和轮询。
- `seedance-ark`：直连火山方舟官方，分开处理视频 API Key、素材 AK/SK、已有真人素材与 H5 认证。
- `seedance-bd`：直连百度 AI 网关的 Seedance 兼容视频、素材与 H5；不混用千帆 QF、VOD 或火山凭据。
- `doubao-web-video`：不开 API Key，用浏览器自动化操作豆包网页版出片并下载。
- `zero-cost-video`：从零合成「底图 + 弹幕 + 多人 TTS」短片，不调用付费 API。
- `video-post-production`：加工已有视频，不负责生成新视频。
- `xiaoice-digital-human`：小冰数字人播报、形象/声音训练和任务管理。

这些 Skill 的输入和任务状态不同，不要在调用时互相替代。

`zero-cost-video` 与 `video-post-production` 的分界只有一句：**手上有没有源视频**。
前者输入是文案和底图，后者必须有视频文件。两者技术栈有重叠（都用 edge-tts 与 ffmpeg amix），
但**编码器假设相反**——前者假定目标机无 `libx264`、只能用 `libopenh264`，后者硬编码 `libx264 + CRF`。
两套参数不能在同一台机器上互换，详见 `zero-cost-video/references/与后处理的边界.md`。

`seedance-video` 负责生成工作流；`seedance-ark` 和 `seedance-bd` 负责供应商接入、素材控制面及真实连通性核验。`doubao-web-video` 则走用户已登录的豆包网页版。三类通道的凭据、端点与验收结论不可互换。

### 专家包（Expert Package）

- `expert-tutorial-video-director`（教程片厂）：**Agent 型专家包，不是单个 Skill**。目录里是完整的专家包结构——`.codebuddy-plugin/plugin.json` + `agents/` + `skills/` + `avatars/`，可整包导入 WorkBuddy 专家中心；内层技能是 `skills/tutorial-video-pipeline`（SVG 讲义卡、录屏、配音、字幕、出片的脚本与规范都在这里）。

它和 `video-post-production` 的分界只有一句：**手上有没有成片之前的素材**。
`video-post-production` 只管已有视频的二次加工；这个专家包从「一个主题」开始——分集大纲、分镜台词、讲义卡与 PPT、浏览器实拍、配音字幕，最后才把 `beats.json` 交给渲染器。内层 `skills/tutorial-video-pipeline/scripts/video_pipeline.py` 是 `video-post-production` 渲染器的原样副本，两端参数一致，不要分头改。

同步口径：改完先更新 `~/.workbuddy/plugins/marketplaces/my-experts/plugins/tutorial-video-director` 并重跑 `validate_expert.py` + `register_expert.py`，再整目录覆盖到这里，两边保持逐字节一致。

### 百度渠道

- `baidu-vod-qianfan`：真实探测旧 VOD、新 VOD、千帆 QF 和 AI 网关 Seedance，并生成 new-api 渠道配置建议。
- `seedance-bd`：只处理百度 AI 网关的 Seedance 视频与素材协议；需要排查旧/新 VOD 或千帆聊天时仍使用上一项。

实际生成工作流仍由 `seedance-video` 负责；百度 AI 网关的直连接口与素材排查使用 `seedance-bd`，千帆 FireSeries、VOD 和聊天渠道差异继续使用 `baidu-vod-qianfan`。不要把聊天接口和视频任务接口混为一个端点。

### Windows 操作

- `windows-computer-use`：通用 Windows UI Automation 和输入注入。
- `trae-computer-use`：Trae/TraeWork 专属适配层，包含 Trae 后端和工具调用方式。

Trae Skill 可以借鉴通用 Windows Skill，但不能假设其他 Windows 工具具备 Trae 的后端。

### 创业与经营

- `xunzhao-chuangye-xiangmu`（创业全流程）：从「我适不适合创业」到「一份能交的创业计划书」，11 个阶段＋一套横切的 AI 取证方法。

主文件只做阶段路由与全局硬规则，内容按需加载到 8 个 references：理论层（判断尺子）、阶段细则（1–6 找项目）、市场分析（7）、开办与运营（8–10）、创业计划书（11）、模块地图、输出模板、AI 赋能。

`scripts/calc_unit_economics.py` 是唯一的脚本：输入售价、进货、佣金、支付费率、履约、退货率、推广、固定成本与预计销量，输出成本结构表、贡献毛利、毛利率、盈亏平衡月销量、安全边际、三档情景（客流 −30% / 成本 +20% / 两者同时），并直接生成可粘贴的 03 档案片段与 `98_证据台账` 行。

它是**可选加速器，不是必需品**：技能允许心算，但要求把公式、每步基数、单位与中间值写出来，判断权交给用户；多档情景、反复调参时才用脚本提速。用了脚本同样要贴输入口径与输出。

三个必停点：阶段 6（已有一个经过对比和算账的项目）、阶段 8（已有市场定位）、阶段 10（已在运营）。**一次只推进一个阶段**，状态写在 `创业项目档案/_进度.md` 里，支持隔天断点续跑。

`references/AI赋能.md` 是**唯一一个可以跨技能复用**的部分：五级降级取数阶梯（L1–L5）、"足不出户"的替代取证表、**统计数据的认源与认口径（S1–S4 / 口径六问 / 年份三坑）**、0–10 分可信度打分卡、多模型交叉验证三层法、98 证据台账。任何需要"查不到数据时怎么办"或"这个行业规模数字能不能用"的技能都可以引用它，不必重写。核心结论只有一句：**AI 输出的证据等级上限是 B，A 级必须靠真实交易与实地走访。**

> 目录名沿用拼音 slug（`xunzhao-chuangye-xiangmu`）而不用英文——上架包与提交记录已用该 name，改名会造成同一技能两个身份。

### 生活决策

- `food-radar`（美食雷达）：把「XX 最好吃的是哪家」拆成可核验的事实——门牌地址、招牌菜归属、人均、分时段营业时间，剔除同名异地与过期数据，输出一张能直接照着走的决策表。

它不评价「哪家更好吃」，只回答「哪家值得专门跑一趟」：主观评价留给用户，客观项必须查实。与内容创作类技能正交——探店文案走 `xhs-note-studio` / `douyin-script-studio`，这里只管行前核查。

`scripts/radar.py` 是唯一的脚本（零依赖，标准库）：管理候选池、跑四项硬判定、按早/午/晚/宵夜出表。数据落在工作目录的 `.food-radar/`，跟着项目走，跨会话不丢。

三个 references 各自承包一块：`browser-capabilities.md` 讲清浏览器这一层能做到什么、做不到什么（**不能执行 JS、不能抓网络层、不能并发**），`sample.md` 是一次完整的江南西炒牛河核验记录，`manual.md` 是不依赖任何工具的手动挡。

> 前置：WorkBuddy 已连接浏览器扩展（`type: "extension"`），点评类站点已登录。缺任何一项仍可走 `manual.md`，流程不残。

### 工具型 Skill

- `grid-image-splitter`：宫格图片切分，保持独立、短流程和明确输入输出。

## 维护规则

- Skill 名称使用小写字母、数字和连字符，目录名与 frontmatter 的 `name` 一致。
- `SKILL.md` 只写触发条件、关键边界和最短工作流；长篇资料放到引用文件。
- YAML frontmatter 使用 `name`、`description` 两个规范字段，并**必须**带上 `agent_created: true`（WorkBuddy 的 `skill_manage` 依赖它才能修改或删除 Skill；其他平台会忽略该字段）。其余可选字段：`license`、`metadata`、`allowed-tools`。
- **需要上架 WorkBuddy 技能市场的 Skill，还要额外补齐 5 个字段**，否则上传 zip 会直接解析失败：`display_name`（中文展示名）、`display_name_en`（英文展示名）、`description_zh`（简短中文介绍）、`description_en`（简短英文介绍）、`version`（如 `1.0.0`）；`author` 为必填。这些字段必须是**顶层键**，写在 `metadata:` 下面不生效。`agent_created: true` 可以与之共存，平台会忽略它。
- **市场详情页的「试试这样问我」由 `examples_zh` / `examples_en` 两个数组字段填充**，不写就显示 `-`。写法照已上架技能的实际惯例：各 3 条、中文单条约 10–19 字、动词开头的具体场景句（不要写成功能描述）。这两个字段在管理后台的表单里没有输入框，只能通过 frontmatter 传入，改完必须重新提交包。
- **上架的 Skill 只允许 4 个顶层条目**：`SKILL.md`、`references/`、`scripts/`、`templates/`。`assets/`、`examples/`、`agents/` 等目录不在这份白名单里，打包时会被平台判为异常或直接忽略，示例数据请放进 `references/`。
- 打包后再自查一遍：zip 内路径必须是正斜杠（`food-radar/SKILL.md`），根目录必须就是 `{skill-name}/`。
- 不在 Skill 中写入真实 API Key、Cookie、长期有效的私有凭据或未经确认的生产地址。
- 真实请求、费用和外部写操作必须保留用户授权边界；测试脚本只输出脱敏结果。

