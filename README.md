# Clover Skills

这个目录保存可直接被 WorkBuddy（以及 Codex 等支持 Agent Skills 的工具）发现的独立 Skill。每个 Skill 都必须是一个目录，并包含 UTF-8 编码的 `SKILL.md`；较长的流程、平台差异、示例和脚本放在 `references/`、`scripts/` 或 `assets/` 中。

## 开发与客户交付边界

- 自用接口开发、集成和业务逻辑技能使用 `-dev` 标识；与客户/用户交付包分开维护，不直接改名覆盖交付包。
- `baidu-api-dev` 是百度开发统一入口及唯一百度接口事实源，已合并原 `baidu-vod`、`baidu-qianfan`、`baidu-vod-qianfan`、`seedance-bd`；旧入口仅作历史，不再活跃，协议和凭据在内部仍分别管理。
- `seedance-dev` 是自用 Seedance 接口整合入口；华锐开发唯一事实源为 `huarui-dev`，不读取客户包或内部视频包。
- 华锐三类边界：`huarui-dev` 仅记录 `C:\code\cloverapi` 内部开发功能（百度 AI Gateway、Seedance、工作台与 OAuth 路线），不作为对外接口包且不含客户配置；`huarui-zhisuan` 是客户交付包，内容保持独立且不改；`huarui-video` 是华锐内部官方真人视频生成包，承接内部 hardcode Key 和真人素材，仅限内部使用，不是通用入口。
- `juhe-nexgate` 是客户开发交付包，面向已部署聚合 API 的运行时调用；客户包 hardcode 配置只能按明确交付约定保留在原包内，不得复制、迁移或放入开发包。
- `juhe-nexgate-dev` 是 Juhe 国内版自用开发入口：`C:/code/mcwlapi`（new-api 网关，接百度/阿里/火山）+ `C:/code/mcwlcpa`（CLIProxyAPI 授权 GPT/Claude 账号池），覆盖渠道、模型映射、计费、CPA v8/旧版配置、部署与验收；不改客户交付包。
- `workbuddy-tutorial` 是视频录制与制作的 WorkBuddy 专家包，保留原目录结构及内置技能，不参与华锐重组。

## 推荐的技能边界

### 内容与媒体创作

内容创作和图片视频创作已分别收敛为两个 WorkBuddy 专家包，避免同一能力同时暴露为大量独立触发入口：

- `workbuddy-selfmedia`：自媒体创作专家。按抖音、快手、视频号、小红书、公众号、头条和双对象横评等平台/文体路由，内置原内容创作技能与参考资料。
- `media-creator`：图片视频创作专家。按 Seedance 生成、华锐开发、视频后处理、数字人、宫格切图和零成本视频规划路由，内置对应技能与参考资料。

专家包已注册到 WorkBuddy 专家目录，并同步保存在本仓库的 `workbuddy-selfmedia/` 与 `media-creator/`；仓库不再保留上述能力的独立副本。需要分享或迁移时，使用 `outputs/workbuddy-selfmedia.zip` 和 `outputs/media-creator.zip`。同步时以专家目录为源，先更新专家包，再复制到本仓库。

仍保持独立的媒体能力：

- `workbuddy-image`：独立图片生成技能，按要求保留，不并入 `media-creator`。
- `doubao-web-video`：豆包网页版视频生成，依赖浏览器自动化，不使用 API Key，按要求保留独立入口。

`seedance-dev`、`baidu-api-dev`、`huarui-dev`、`huarui-zhisuan` 与 `huarui-video` 仍按开发、客户交付和内部使用边界独立维护；它们不是普通媒体技能的重复副本。客户包的 hardcode Key 与账号素材不得迁入开发入口；各通道的凭据、端点、素材归属与验收结论不可互换。

### 专家包（Expert Package）

- `workbuddy-tutorial`（教程片厂）：**Agent 型专家包，不是单个 Skill**。目录里是完整的专家包结构——`.codebuddy-plugin/plugin.json` + `agents/` + `skills/` + `avatars/`，可整包导入 WorkBuddy 专家中心。

里面是三个单一职责技能，按「能不能单独交付」切，不按步骤切：

| 技能 | 管什么 | 单独可用 |
|---|---|---|
| `tutorial-series-plan` | 立项、分集、分镜台词（`series.json` / `beats.json`），纯文字 | 要大纲脚本 |
| `svg-lecture-deck` | SVG 卡 + 渲染 PNG + 导 PPTX，任意画布 | 只要一份能改字的 PPT |
| `tutorial-video-assemble` | 录屏、配音、字幕、出片 | 把素材剪成片 |

唯一的共享契约是 `beats.json`，权威定义在 `tutorial-video-assemble/references/beats契约.md`。

**三个技能互不依赖，各自自包含**：`canvas.py` 三处各一份、`svg2png.py` 两处各一份，是故意重复的——宁可重复，也不让一个技能因为另一个没装而断掉。单独把任意一个目录拷走都能跑。改画布令牌时三份要一起改（`svg-lecture-deck` 里那份算规范源），改完 `md5sum` 对一下；允许暂时不一致，后果只是同一份 `beats` 在不同画布下算出的字号不同。

整个包也不引用任何外部技能：渲染器、画布令牌、SVG→PNG、SVG→PPTX 全在包内。

它与 `media-creator` 的分界只有一句：**手上有没有成片之前的素材**。
`media-creator` 负责已有视频的二次加工；这个专家包从「一个主题」开始——分集大纲、分镜台词、讲义卡与 PPT、浏览器实拍、配音字幕，最后才把 `beats.json` 交给渲染器。内层 `tutorial-video-assemble/scripts/video_pipeline.py` 保留独立副本，避免教程专家脱离 `media-creator` 后无法工作。

画布不锁 1920×1080：`u = min(宽,高)/1080`，令牌全乘 `u`，16:9 / 9:16 / 1:1 / 4:5 / 3:4 / 4K 同一套流程。16:9 时 `u=1`，与旧版逐像素一致。

同步口径：改完先更新 `~/.workbuddy/plugins/marketplaces/my-experts/plugins/workbuddy-tutorial` 并重跑 `validate_expert.py` + `register_expert.py`，再整目录覆盖到这里，两边保持逐字节一致。

- `workbuddy-butler`（WB空间清理大师）：**Agent 型专家包**，人设是"老陈"，只管一件事——WorkBuddy 自己的磁盘占用。目录同样是 `.codebuddy-plugin/plugin.json` + `agents/` + `skills/` + `avatars/` 的完整专家包结构。

它内置单一技能 `workbuddy-disk-audit`，四个脚本各管一段，互不依赖：

| 脚本 | 管什么 |
|---|---|
| `scan_space.py` | 盘清 `.workbuddy`、Roaming、安装目录、旧版本残留四处总量，一级目录按 A/B/C/D 打标，按工作空间归组算会话占用 |
| `purge.py` | `SHFileOperationW` 永久删除（不带 `FOF_ALLOWUNDO`），默认拒绝盘根、`workbuddy.db`、`binaries`、`blobs` |
| `recycle_audit.py` | 解析 `$I*` 元数据还原被删路径，`--match` 精确筛，`--purge` 永久删 |
| `session_clean.py` | 软删除会话残留清理、工作空间记录裁剪，改库前自动 sqlite 备份 |

核心约束写在 Agent 正文里：**收益只认 `disk_usage` 前后差值**，必须分栏报"移动量 / 进回收站量 / 真正释放量"，不许拿移动量冒充释放量；改库前先 sqlite backup；`binaries`、`blobs`、`workbuddy.db` 一律不碰。

`references/已知坑位.md` 沉淀了 10 个真踩过的坑，其中三条值得单独记：本机 python 的删除可能被 safe-delete 垫片重定向到回收站（`rmtree` 后目录"消失"但空间没少）、同盘移动不释放空间、`%USERPROFILE%\WorkBuddy` 是旧版安装残留而不是临时工作区。

同步口径同上：先改专家目录、重跑 `validate_expert.py` + `register_expert.py`，再整目录覆盖到本仓库。

### 百度渠道（开发）

- `baidu-api-dev`：统一旧 VOD、新 VOD、千帆 QF、AI 网关 Seedance 的接口开发、最小测试及 new-api 渠道集成。
- 原四个技能已合并，不保留重复激活入口；旧主文件作为 `references/legacy-*.md` 保存供追溯。
- VOD 聊天、QF FireSeries、网关视频任务/素材/H5分别按需加载资料；合并技能不等于合并端点、账号、凭据或计费权限。
- 三个 Python CLI 和 PowerShell 探测脚本均保留；真实计费、外部写入及批量探测必须按当前用户授权执行。

### Windows 操作

- `computer-use`：统一 Windows 电脑控制技能，覆盖桌面应用、浏览器、IDE、办公软件和 Trae/TraeWork 场景；按后端选择 UI Automation、坐标注入或 computer-use MCP。

原 `windows-computer-use` 与 `trae-computer-use` 已合并到 `computer-use`，不再保留两个重复激活入口。

### 创业与经营

- `workbuddy-business`（商业全流程）：从「我适不适合创业」到「一份能交的创业计划书」，覆盖项目寻找、开办、运营、履约、财务与风险控制。

主文件只做阶段路由与全局硬规则，内容按需加载到 8 个 references：理论层（判断尺子）、阶段细则（1–6 找项目）、市场分析（7）、开办与运营（8–10）、创业计划书（11）、模块地图、输出模板、AI 赋能。

`scripts/calc_unit_economics.py` 是唯一的脚本：输入售价、进货、佣金、支付费率、履约、退货率、推广、固定成本与预计销量，输出成本结构表、贡献毛利、毛利率、盈亏平衡月销量、安全边际、三档情景（客流 −30% / 成本 +20% / 两者同时），并直接生成可粘贴的 03 档案片段与 `98_证据台账` 行。

它是**可选加速器，不是必需品**：技能允许心算，但要求把公式、每步基数、单位与中间值写出来，判断权交给用户；多档情景、反复调参时才用脚本提速。用了脚本同样要贴输入口径与输出。

三个必停点：阶段 6（已有一个经过对比和算账的项目）、阶段 8（已有市场定位）、阶段 10（已在运营）。**一次只推进一个阶段**，状态写在 `创业项目档案/_进度.md` 里，支持隔天断点续跑。

`references/AI赋能.md` 是**唯一一个可以跨技能复用**的部分：五级降级取数阶梯（L1–L5）、"足不出户"的替代取证表、**统计数据的认源与认口径（S1–S4 / 口径六问 / 年份三坑）**、0–10 分可信度打分卡、多模型交叉验证三层法、98 证据台账。任何需要"查不到数据时怎么办"或"这个行业规模数字能不能用"的技能都可以引用它，不必重写。核心结论只有一句：**AI 输出的证据等级上限是 B，A 级必须靠真实交易与实地走访。**

> 技术标识采用短英文 slug `workbuddy-business`，展示名使用 `WorkBuddy商业专家组`，便于在 WorkBuddy 专家中心识别和调用。

### 生活决策

- `workbuddy-food`（美食雷达）：把「XX 最好吃的是哪家」拆成可核验的事实——门牌地址、招牌菜归属、人均、分时段营业时间，剔除同名异地与过期数据，输出一张能直接照着走的决策表。

它不评价「哪家更好吃」，只回答「哪家值得专门跑一趟」：主观评价留给用户，客观项必须查实。与内容创作类能力正交——探店文案走 `workbuddy-selfmedia`，这里只管行前核查。

`scripts/radar.py` 是唯一的脚本（零依赖，标准库）：管理候选池、跑四项硬判定、按早/午/晚/宵夜出表。数据落在工作目录的 `.food-radar/`，跟着项目走，跨会话不丢。

三个 references 各自承包一块：`browser-capabilities.md` 讲清浏览器这一层能做到什么、做不到什么（**不能执行 JS、不能抓网络层、不能并发**），`sample.md` 是一次完整的江南西炒牛河核验记录，`manual.md` 是不依赖任何工具的手动挡。

> 前置：WorkBuddy 已连接浏览器扩展（`type: "extension"`），点评类站点已登录。缺任何一项仍可走 `manual.md`，流程不残。

### 工具型能力

宫格图片切分已并入 `media-creator`，不再作为仓库根目录的独立 Skill 暴露。

## 维护规则

- Skill 名称使用小写字母、数字和连字符，目录名与 frontmatter 的 `name` 一致。
- `SKILL.md` 只写触发条件、关键边界和最短工作流；长篇资料放到引用文件。
- YAML frontmatter 使用 `name`、`description` 两个规范字段，并**必须**带上 `agent_created: true`（WorkBuddy 的 `skill_manage` 依赖它才能修改或删除 Skill；其他平台会忽略该字段）。其余可选字段：`license`、`metadata`、`allowed-tools`。
- **需要上架 WorkBuddy 技能市场的 Skill，还要额外补齐 5 个字段**，否则上传 zip 会直接解析失败：`display_name`（中文展示名）、`display_name_en`（英文展示名）、`description_zh`（简短中文介绍）、`description_en`（简短英文介绍）、`version`（如 `1.0.0`）；`author` 为必填。这些字段必须是**顶层键**，写在 `metadata:` 下面不生效。`agent_created: true` 可以与之共存，平台会忽略它。
- **市场详情页的「试试这样问我」由 `examples_zh` / `examples_en` 两个数组字段填充**，不写就显示 `-`。写法照已上架技能的实际惯例：各 3 条、中文单条约 10–19 字、动词开头的具体场景句（不要写成功能描述）。这两个字段在管理后台的表单里没有输入框，只能通过 frontmatter 传入，改完必须重新提交包。
- **上架的 Skill 只允许 4 个顶层条目**：`SKILL.md`、`references/`、`scripts/`、`templates/`。`assets/`、`examples/`、`agents/` 等目录不在这份白名单里，打包时会被平台判为异常或直接忽略，示例数据请放进 `references/`。
- 打包后再自查一遍：zip 内路径必须是正斜杠（`workbuddy-food/SKILL.md`），根目录必须就是 `{skill-name}/`。
- 自用开发与公开通用 Skill 不写入真实 API Key、Cookie 或未经确认的生产地址；客户专用交付包可按明确交付约定内置指定 Key，但不得跨客户/开发包复用、在报告中回显或未经授权扩大分发。
- 真实请求、费用和外部写操作必须保留用户授权边界；测试脚本只输出脱敏结果。

