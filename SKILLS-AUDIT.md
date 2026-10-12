# clover-skills 规范体检与整理方案

首轮体检：2026-10-16 00:56
复查更新：2026-10-16 01:10
**执行更新：2026-10-16 01:12（仓库定位＝服务 WorkBuddy）**
对标规范：WorkBuddy/CodeBuddy `skill-creator`（`SKILL.md` + `scripts/` + `references/` + `assets/`，frontmatter 必含 `name`/`description`/`agent_created`）

---

## 本轮已执行（01:12）

用户确认仓库服务于 **WorkBuddy**，已完成以下 4 项：

| # | 动作 | 结果 |
|---|---|---|
| 1 | 14 个 `SKILL.md` 全部补回 `agent_created: true` | ✅ 14/14 通过校验 |
| 2 | `README.md` 改为 WorkBuddy 口径 | ✅ 第 3 行改为「WorkBuddy（及 Codex 等）」，字段规范那行补上 `agent_created` 说明 |
| 3 | `README.md` 补收录 `find-your-project` | ✅ 新增「工作区定位」分类，收录 14/14 |
| 4 | 修 `xiaoice-digital-human` 坏链 | ✅ 删除不存在的 `scripts/deploy-nginx.conf` 引用 |
| 5 | 拆分 `xiaoice-digital-human` 主文件 | ✅ 739 行 / 39KB → **130 行 / 8.7KB** + 6 个 references（32.4KB） |

**拆分后的 `xiaoice-digital-human`**（主文件只留路由骨架，内容按需加载）：

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
| 健康 | 12 | xhs / toutiao / wechat-mp / douyin / kuaishou / wxchannels / grid-image-splitter / seedance-video / video-post-production / windows-computer-use / trae-computer-use / find-your-project |
| 需重构 | 1 | `xiaoice-digital-human`（主文件 739 行 + 坏链） |
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

### 5. `xiaoice-digital-human` 根目录散落文件（未处理）

`avatars_page1.json` / `page2` / `page3` 直接躺在 skill 根目录，应移到 `assets/`。

### 6. `video-post-production/references/` 混入开发过程文档（未处理）

`tests报告.md`、`安全审计报告.md`、`升级说明.md` 三份是**开发自证材料，不是给 agent 执行任务用的参考**，会让 AI 误判为任务输入。建议移出 skill 目录（放仓库 `docs/dev/`）。

### 7. `seedance-video` 无 `references/`（未处理）

126 行主文件里塞了完整 API 表格、请求体、素材限制、模型 ID。应拆到 `references/api.md`。

### 8. `video-post-production` 的 5 个 assets JSON 为泛引用（未处理）

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
| `seedance-video` / `video-post-production` / `xiaoice-digital-human` | 不合并。生成 / 二次加工 / 数字人是三种不相交能力，README 也已说明 |
| `windows-computer-use` + `trae-computer-use` | 保持分立。已是正确的"通用 + 适配"分层 |

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
│   ├── windows-computer-use/
│   └── trae-computer-use/
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
| ⬜ | P1 | 移出 `video-post-production` 三份开发文档 | 防止 AI 误读为任务输入 |
| ⬜ | P1 | `baidu-vod-qianfan/agents/` 处置 | 规范外的死文件 |
| ⬜ | P1 | `xiaoice` 根目录 3 个 `avatars_page*.json` | 实为 `scripts/01-list-avatars.sh` 的运行产物，混在源目录里 |
| ⬜ | P2 | 建 `_templates/` + 同步脚本（方案 C） | 降低 6 工坊维护成本 |
| ⬜ | P2 | 仓库目录按 6 大类分组 | 可读性 |
| ⬜ | P2 | `trae-computer-use` 隔离（平台错配，WorkBuddy 下跑不起来） | 会被误触发 |

---

## 七、待确认

1. ~~本仓库的主服务对象是 WorkBuddy 还是 Codex？~~ → **已定：WorkBuddy**
2. 是否仍有 Trae 使用场景？—— 决定 `trae-computer-use` 去留
3. 6 个工坊是否采用方案 C（`_templates/` 事实源）？
4. 仓库改动是否需要同步回 `~/.workbuddy/skills/`？
