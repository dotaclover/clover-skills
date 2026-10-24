# clover-skills 规范体检与整理方案

首轮体检：2026-10-16 00:56
复查更新：2026-10-16 01:10
**执行更新：2026-10-16 01:12（仓库定位＝服务 WorkBuddy）**
对标规范：WorkBuddy/CodeBuddy `skill-creator`（`SKILL.md` + `scripts/` + `references/` + `assets/`，frontmatter 必含 `name`/`description`/`agent_created`）

---

## 新增 juhe-nexgate-dev（国内版开发）

- 以本地 `mcwlapi`、`mcwlcpa` 源码与仓库文档为依据，新增独立开发技能；保留 `juhe-nexgate` 客户运行时调用包不变。
- 主入口 + 6 篇 references：架构、网关开发、国内供应商、授权账号池、部署、验收与排障。
- 明确 new-api 负责百度/阿里/火山渠道与统一业务账本，CLIProxyAPI 负责 GPT/Codex、Claude 授权账号池。
- 明确 CPA 主模板 v8 与历史顶层配置的兼容差异，区分四层凭据，不复制真实账号凭据或生产配置。
- 仅做技能静态验证与打包；没有修改两个业务项目、执行授权登录、真实推理或部署。

## 2026-10-18 新增 workbuddy-food（v2.4.0）

| # | 动作 | 结果 |
|---|---|---|
| 1 | 新增 `workbuddy-food`（美食雷达） | 1 个目录 / 6 个文件 / 47KB |
| 2 | 按仓库三类目录规范整理 | 原 `examples/` 拆成 `references/sample.md` + `assets/sample-pool.json` |
| 3 | 主文件拆分 | 275 行 / 15.8KB → **218 行 / 12.0KB** + 3 个 references |
| 4 | frontmatter 按仓库口径 | `name` / `description` / `agent_created` / `metadata`（display_name、category、version、author） |
| 5 | README 新增「生活决策」分类 | 收录 1 个 |
| 6 | 技能总数 | 19 → 20 |

**结构**：主文件只保留每轮必用的部分——前置条件、输入三要素、五步执行流程、四项硬核验、已知坑、路由表；能力边界（44 行）、实测样例（70 行）、手动挡（31 行）按需加载。

**为什么拆**：这三块都是「查的时候才看」而非「每次都要看」。拆完主文件 12.0KB，与 `workbuddy-business`（12KB）持平。历史记录保留当时的拆分结论；该团队技能同时作为 `media-creator` 专家包的业务能力来源。

**能力边界的价值**：这一节记的是实测结论，不是推测——`cua_execute` 只能排坐标动作和截图、**没有 JS eval 入口**，所以 `document.body.innerText` 这条路根本不存在；大众点评的评分数字用自定义字体加密，DOM 文本取到的是 PUA 乱码，**截图 + 多模态读图反而是唯一低成本解**。不写下来，下次还会有人试着用 innerText 一把梭。

**与 `ai-answer-audit` 的关系**：无依赖。候选可以来自用户随口报的店名，不需要先跑任何审计；审计技能也不产出店铺结论。两者只在「都需要浏览器扩展 + 站点登录态」这一点上重合。`ai-answer-audit` 目前只在用户级目录、未进本仓库。

**脚本定位**：`scripts/radar.py`（566 行，零依赖）不操作浏览器——那是 MCP 独占通道，脚本另起 Playwright 会丢登录态。它只做 MCP 做不到的那部分：跨会话持久化、四项判定、时段解析、排序出表。README 里那句「脚本替代的是记性和算账」就是这条边界的总结。

---

## 2026-10-18 修订（v2.3.0）

| # | 动作 | 结果 |
|---|---|---|
| 1 | `AI赋能.md` 新增**第四节：统计数据**（认源 S1–S4 / 口径六问 / 年份三坑 / 提问模板 / 三源对齐），原四–十顺延为五–十一 | 19.2KB → 26KB，375 → 527 行 |
| 2 | 修正「越具体越可疑」的适用范围 | 该判据对统计公报不成立（公报数字本就带小数）；判据改为"能否回原文对账" |
| 3 | 心算规则降级 | 原「禁止让模型心算」→「心算可以，但公式、基数、单位、中间值必须写出来」；脚本从"必须"改为"可选加速器" |
| 4 | 删除 `find-your-project` | 按用户判断移除；技能总数 19 → 18，README 的「工作区定位」分类与边界说明一并删除 |
| 5 | 版本 | 2.2.0 → 2.3.0，工作区上架副本与仓库副本同步（正文逐字节一致） |

**判断依据**：用户明确「模型心算是 OK，用户自己判断」——技能的职责是交出可判断的过程，不是替用户做算术保险。
同时明确本案的核心是**统计数据**：这类数据有公开源，AI 网页版能检索到，难点不在"有没有"而在"是不是原始发布方、口径对不对、年份有没有被挪"。

---

| # | 动作 | 结果 |
|---|---|---|
| 1 | 重构并新增 `workbuddy-business`（WorkBuddy商业专家组） | 1 个专家包目录 + 共享方法库；六角色协作，课程照片/题库作为方法与验收资料 |
| 2 | frontmatter 按仓库口径收敛 | 顶层只留 `name` / `description` / `agent_created` / `metadata`；原 `display_name`、`display_name_en`、`category`、`version`、`author` 收进 `metadata` |
| 3 | 校验 | 8 个 references 引用全部有效，无坏链、无中文弯引号 |
| 4 | 分类 | `README.md` 新增「创业与经营」，与「工作区定位」并列 |
| 5 | 技能总数 | 18 → 19 |
| 6 | **补 `scripts/calc_unit_economics.py`**（v2.2.0） | 10 个文件 / 58KB。单件成本结构、毛利率、盈亏平衡销量、安全边际、三档情景，并直接生成 03 档案片段与 98 台账行 |
| 7 | 消触发冲突 | description 去掉裸「找项目」，改为「找商机、选项目」，并显式排除「代码项目根目录定位（find-your-project）」 |

**结构**：共享方法库保留阶段路由、证据边界、财务规则、课程资料边界和输出模板；专家包新增项目经理、创始人输入、机会研究、运营推广与美工、客服、采购及仓储物流、财务风控六成员。原始课程照片和测试题保留在原资料目录，不打入专家包。

**跨技能复用点**：`references/AI赋能.md`（19KB）不绑定创业场景，五级降级取数、可信度打分卡、交叉验证三层法可被任何"查不到数据"的技能引用，不必重写。

**为什么补脚本**：技能规则写着「禁止让模型心算百分比、盈亏平衡」，而阶段 3 的成本测算原先只给公式、靠对话心算——规则与流程自相矛盾。脚本把除法、取整、情景叠加全部移出模型。

**剩余待办**：阶段 9 的财务三表仍是 `输出模板.md` 里的空表，未脚本化。是否值得补取决于是否需要"从流水倒推毛利结构"的输入；目前模板够用。

---

## 本轮已执行（01:12）

用户确认仓库服务于 **WorkBuddy**，已完成以下 4 项：

| # | 动作 | 结果 |
|---|---|---|
| 1 | 14 个 `SKILL.md` 全部补回 `agent_created: true` | ✅ 14/14 通过校验 |
| 2 | `README.md` 改为 WorkBuddy 口径 | ✅ 第 3 行改为「WorkBuddy（及 Codex 等）」，字段规范那行补上 `agent_created` 说明 |
| 3 | `README.md` 补收录 `find-your-project` | ✅ 新增「工作区定位」分类，收录 14/14 |
| 4 | 修历史版 `xiaoice-digital-human` 坏链 | ✅ 删除不存在的 `scripts/deploy-nginx.conf` 引用；后续已并入 `media-creator` 专家包 |
| 5 | 拆分 `xiaoice-digital-human` 主文件 | ✅ 739 行 / 39KB → **130 行 / 8.7KB** + 6 个 references（32.4KB） |

**历史拆分后的 `xiaoice-digital-human`**（主文件只留路由骨架，内容按需加载；当前内容已随媒体创作能力迁入 `media-creator` 专家包）：

| 文件 | 大小 | 内容 |
|---|---|---|
| `SKILL.md` | 8.7KB | 路径选择、快速上手、透传校验表、基础约定、能力索引、参考资料路由 |
| `references/endpoints.md` | 9.1KB | 核心接口 + 画布适配公式 |
| `references/editor-mode.md` | 9.7KB | 编辑器完整字段清单 |
| `references/layout-pitfalls.md` | 4.4KB | 版式实测与 6 个坑 |
| `references/dialogue-video.md` | 4.2KB | 双人对谈方案 |
| `references/training.md` | 2.0KB | 形象/声音训练流程 |
| `references/assets-and-timing.md` | 3.0KB | 素材准备、CDN 限制、时长标定 |

校验结果：无坏链、无孤儿 references、6 个引用全部有效。

**仍未处理**：见下方「六、执行优先级」中标记为 ⬜ 的项。

---

## 复查结论（01:10）

**没有新增技能目录，仍是 14 个。** 但仓库状态发生了 4 处变化，其中 2 处是新增问题。

| 变化 | 性质 |
|---|---|
| `find-your-project/` 补上了 `SKILL.md`（31 行） | ✅ 修复：从空壳变为有效 skill |
| 新增 `README.md`（仓库定位 + 维护规则） | 🆕 但引入了规范冲突 |
| **全仓 14 个 skill 的 `agent_created: true` 被删除** | ❌ 恶化：首轮只有 4 个缺，现在 14 个全缺 |
| 仓库改动未同步到 `~/.workbuddy/skills/` | ⚠️ 两边版本已不一致 |

### 当前状态汇总

| 状态 | 数量 | 目录 |
|---|---|---|
| 健康 | 11 | xhs / toutiao / wechat-mp / douyin / kuaishou / wxchannels / grid-image-splitter / seedance-video / video-post-production / computer-use / find-your-project |
| 历史需重构 | 1 | `xiaoice-digital-human`（当时主文件 739 行 + 坏链；当前已迁入 `media-creator`） |
| 空壳 | 0 | ~~find-your-project~~ 已修复 |

---

## 一、新增的两个问题

### 问题 A：README 的字段规范与 WorkBuddy 冲突 ⚠️ 需拍板

`README.md` 第 49 行：

> YAML frontmatter 只使用规范字段：`name`、`description`、`license`、`metadata`、`allowed-tools`。

WorkBuddy 内置 `skill-creator` 第 48 行：

> The YAML frontmatter **MUST** include `agent_created: true` so that `skill_manage` can modify or delete the skill later.

两套规范不一致，根因是**目标平台不同**：README 第 3 行写明「可直接被 **Codex** 发现的独立 Skill」，用的是 Codex / Claude Agent Skills 规范；WorkBuddy 走的是另一套。

**这不是对错问题，是仓库要服务谁的问题。**

**建议：加回 `agent_created: true`。** 理由：
- 它是纯附加布尔字段。Codex 解析 frontmatter 时忽略未知字段，加了**零副作用**；
- 不加则 WorkBuddy 侧**丧失修改/删除这些 skill 的能力**，是净损失；
- 两全做法：README 那句改成「规范字段 + `agent_created`（WorkBuddy 兼容标记，其他平台忽略）」。

### 问题 B：README 漏收录 `find-your-project`

README 分 5 个分类列了 **13 个** skill，实际目录 **14 个**。唯一没进列表的就是新补的 `find-your-project`。

它应该归入一个新分类「工作区定位」，或并入「工具型 Skill」。

### 问题 C：安装目录未同步（附带发现）

`~/.workbuddy/skills/` 下的 6 个 studio **仍是含 `agent_created` 的旧版**，与仓库当前版本不一致。若本次改动是有意为之，需要同步；若是误改，需要回滚。

---

## 二、硬伤

### 1. `agent_created: true` 全仓缺失（首轮 4 个 → 现在 14 个）

首轮体检时 9 个有、4 个缺。本次复查，**14 个全缺**。

- 被删除的：douyin / kuaishou / toutiao / wechat-mp / wxchannels / xhs / video-post-production（7 个，git 有记录）
- 一并消失的：windows-computer-use / trae-computer-use（untracked，无 git 记录）
- 原本就缺的：baidu-vod-qianfan / grid-image-splitter / seedance-video / xiaoice-digital-human
- 新建就缺的：find-your-project

**处理取决于问题 A 的决策。**

### 2. 坏链 1 处（未修）

`xiaoice-digital-human/SKILL.md:122` 引用 `scripts/deploy-nginx.conf`，**该文件不存在**。删引用或补文件。

### 3. 非标准目录 `agents/`（未处理）

`baidu-vod-qianfan/agents/openai.yaml` —— `agents/` 不在规范的三类目录内，内置 skill 无一使用此模式（统一用 `.codebuddy-plugin/plugin.json`）。
内容是界面元数据（`display_name` / `short_description` / `default_prompt`），**WorkBuddy 不读它**。

---

## 三、结构问题

### 4. `xiaoice-digital-human/SKILL.md` 严重超标（未修）

**739 行 / 39KB**，规范建议主文件 < 5k words。中文 39KB 约 1.3 万字，超 4 倍。

| 拆出的内容 | 现有行号 | 目标文件 |
|---|---|---|
| 编辑器模式：完整功能清单 | 274–583（309 行） | `references/editor-mode.md` |
| 视频生成 | 124–273 | `references/video-generate.md` |
| 多角色对话视频 | 583–678 | `references/dialogue-video.md` |
| 形象训练 / 声音训练 | 679–717 | `references/training.md` |
| 素材准备 + 时长标定 | 107–123 / 728–739 | `references/assets-and-timing.md` |

### 5. 历史记录：`xiaoice-digital-human` 根目录散落文件（已随专家包迁移）

`avatars_page1.json` / `page2` / `page3` 直接躺在 skill 根目录，应移到 `assets/`。

### 6. `video-post-production/references/` 混入开发过程文档（未处理）

`tests报告.md`、`安全审计报告.md`、`升级说明.md` 三份是**开发自证材料，不是给 agent 执行任务用的参考**，会让 AI 误判为任务输入。建议移出 skill 目录（放仓库 `docs/dev/`）。

### 7. `seedance-video` 无 `references/`（未处理）

126 行主文件里塞了完整 API 表格、请求体、素材限制、模型 ID。应拆到 `references/api.md`。

### 8. 历史记录：`video-post-production` 的 5 个 assets JSON（已随专家包迁移）

主文件只写"`assets/` 中 JSON 模板"，未点名具体文件。建议逐个列出用途。

---

## 四、合并分析：6 个内容工坊

**结论未变：唯一候选是 6 个工坊，但不建议物理合并。**

### 重复度实测

| 维度 | 事实 |
|---|---|
| 目录结构 | 6 个完全一致：`references/{input-brief, truthfulness, compliance, <平台>playbook}` |
| 主文件 | 同一套模板，179–195 行，8.5–9.3KB，章节名逐字相同 |
| references 内容 | 37 个文件 md5 全不同，但 diff 仅 10–25%，且都是平台特化：`input-brief` 改几个字段名、`truthfulness` 改 1–2 句、`compliance` 增删 1–2 行 |

**结构 100% 复用，内容 75–90% 复用。**

### 三个方案

**方案 A：抽公共底座到 `_shared/`** —— ❌ 不可行
每个工坊都写着"自洽独立、可单独分发"，且安装后是单目录平铺，跨目录引用必然失效。

**方案 B：合并成单个 `content-studio`** —— ❌ 不推荐
description 要覆盖 6 平台全部触发词，会膨胀到 600+ 字符且互相干扰，触发精度下降；用户说"写抖音脚本"却要加载 130KB 全平台 references，context 成本翻倍。

**方案 C：保持独立，仓库侧建单一事实源** —— ✅ 推荐
新增 `_templates/` 存公共段落骨架 + 同步脚本渲染进各工坊 `references/`。改一条通用规则只需改一处，不破坏任何 skill 的自洽性。

> 注：README 已明确写了「不要把六个平台合并成一个无差别的触发入口」，与方案 C 结论一致。

### 另外两组不该合并

| 候选 | 判断 |
|---|---|
| `seedance-dev` / `media-creator` | 已按用户确认合并为图片视频创作专家；生成、二次加工、数字人仍在专家内部保持独立路由 |
| `windows-computer-use` + `trae-computer-use` | 已合并为 `computer-use`，统一通用 Windows 操作与 Trae 适配层 |

---

## 五、分类整理方案

**关键约束**：WorkBuddy 加载 skill 是扫描 skills 目录的**直接子目录**，**不支持嵌套**。仓库侧可分组建目录，安装侧必须平铺到 `~/.workbuddy/skills/<skill-name>/`。

README 现有的 5 分类（内容创作 / 视频与数字人 / 百度渠道 / Windows 操作 / 工具型）方向正确，但**漏了 `find-your-project`**，且「视频与数字人」「百度渠道」可以再拆得更清楚。

建议：

```
clover-skills/
├── content-studio/           # 内容创作（6）
│   ├── xhs-note-studio/
│   ├── toutiao-article-studio/
│   ├── wechat-mp-studio/
│   ├── douyin-script-studio/
│   ├── kuaishou-script-studio/
│   └── wxchannels-script-studio/
├── media-generation/         # 媒体生成（2）
│   ├── seedance-video/
│   └── xiaoice-digital-human/
├── media-processing/         # 媒体加工（2）
│   ├── video-post-production/
│   └── grid-image-splitter/
├── desktop-automation/       # 桌面自动化（2）
│   └── computer-use/
├── workspace/                # 工作区定位（1）← README 漏收录
│   └── find-your-project/
├── api-integration/          # 厂商 API 接入（1）
│   └── baidu-vod-qianfan/
└── _templates/               # 工坊公共段落事实源（方案 C）
```

---

## 六、执行优先级

| 状态 | 优先级 | 动作 | 影响 |
|---|---|---|---|
| ✅ | P0 | 拍板问题 A：本仓库服务 WorkBuddy | 已定，按 WorkBuddy 口径 |
| ✅ | P0 | 修 `xiaoice` 的 `deploy-nginx.conf` 坏链 | 已删引用 |
| ✅ | P0 | README 补收录 `find-your-project` | 已补，14/14 |
| ✅ | P0 | 14 个 skill 补回 `agent_created: true` | 已补，14/14 |
| ✅ | P1 | 拆分 `xiaoice` 主文件 | 739 行 → 130 行 + 6 references |
| ⬜ | P1 | 确认 `~/.workbuddy/skills/` 是否需要同步 | 两边版本已不一致（仓库已改，安装目录仍是旧版） |
| ✅ | 已完成 | 将 `video-post-production` 及相关媒体能力迁入 `media-creator` 专家包并删除仓库根目录独立副本 | 精简根目录，专家内部仍保留完整资料 |
| ⬜ | P1 | `baidu-vod-qianfan/agents/` 处置 | 规范外的死文件 |
| ⬜ | P1 | `xiaoice` 根目录 3 个 `avatars_page*.json` | 实为 `scripts/01-list-avatars.sh` 的运行产物，混在源目录里 |
| ⬜ | P2 | 建 `_templates/` + 同步脚本（方案 C） | 降低 6 工坊维护成本 |
| ⬜ | P2 | 仓库目录按 6 大类分组 | 可读性 |
| ✅ | P2 | 合并 `windows-computer-use` 与 `trae-computer-use` 为 `computer-use` | 统一各种 Windows 与 Trae 场景，避免重复入口 |

---

## 七、待确认

1. ~~本仓库的主服务对象是 WorkBuddy 还是 Codex？~~ → **已定：WorkBuddy**
2. 是否仍有 Trae 使用场景？—— 决定 `trae-computer-use` 去留
3. 6 个工坊是否采用方案 C（`_templates/` 事实源）？
4. 仓库改动是否需要同步回 `~/.workbuddy/skills/`？
