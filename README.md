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

### 视频与数字人

- `seedance-video`：生成新视频、参考素材、编辑/延长、提交和轮询。
- `video-post-production`：加工已有视频，不负责生成新视频。
- `xiaoice-digital-human`：小冰数字人播报、形象/声音训练和任务管理。

这三个 Skill 的输入和任务状态不同，不要在调用时互相替代。

### 百度渠道

- `baidu-vod-qianfan`：真实探测旧 VOD、新 VOD、千帆 QF 和 AI 网关 Seedance，并生成 new-api 渠道配置建议。

Seedance 视频属于 `seedance-video`；百度 AI 网关、千帆 FireSeries 等视频提供商差异应放在 Seedance 的参考资料中，不要把聊天接口和视频任务接口混为一个端点。

### Windows 操作

- `windows-computer-use`：通用 Windows UI Automation 和输入注入。
- `trae-computer-use`：Trae/TraeWork 专属适配层，包含 Trae 后端和工具调用方式。

Trae Skill 可以借鉴通用 Windows Skill，但不能假设其他 Windows 工具具备 Trae 的后端。

### 工作区定位

- `find-your-project`：把用户给的项目线索（项目名、目录片段、多个候选）解析为可验证的项目根目录，并在开始编码、部署、测试或写文档前读取该目录的本地协作规则。

### 工具型 Skill

- `grid-image-splitter`：宫格图片切分，保持独立、短流程和明确输入输出。

## 维护规则

- Skill 名称使用小写字母、数字和连字符，目录名与 frontmatter 的 `name` 一致。
- `SKILL.md` 只写触发条件、关键边界和最短工作流；长篇资料放到引用文件。
- YAML frontmatter 使用 `name`、`description` 两个规范字段，并**必须**带上 `agent_created: true`（WorkBuddy 的 `skill_manage` 依赖它才能修改或删除 Skill；其他平台会忽略该字段）。其余可选字段：`license`、`metadata`、`allowed-tools`。
- 不在 Skill 中写入真实 API Key、Cookie、长期有效的私有凭据或未经确认的生产地址。
- 真实请求、费用和外部写操作必须保留用户授权边界；测试脚本只输出脱敏结果。

