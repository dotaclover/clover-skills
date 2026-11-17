# 顺哥自媒体

顺哥个人号的自媒体专家包。当前只含小红书，其余平台按顺序逐个追加。

## 现有能力

| 平台 | 技能 | 能做什么 |
|---|---|---|
| 小红书 | `xhs-note-studio` | 选题→标题→正文→封面→配图→违禁词体检；旧笔记诊断；评论区回复 |

## 前置：账号卡

`~/.workbuddy/xhs-profile.md`，用户级文件，不在本包内。存在则读，不存在退回零预设。

账号卡管人设、赛道、读者层、雷区、语言排版，与技能默认值冲突时以卡为准。

## 追加平台

三步，别临时发挥：

1. 从仓库根目录的同名技能目录复制进本包 `skills/`（如 `../wxchannels-script-studio`）
2. `plugin.json` 的 `skills` 数组加一行
3. `agents/shunge-selfmedia.md` 里把该平台从「后续平台」表移到「现有平台」表

计划顺序：视频号 → 抖音 → 快手 → 公众号 → 微头条。每加一个，版本号 +0.1.0。

## 发布

真源在本目录。发布做两件事：

1. 整个目录复制到 `~/.workbuddy/plugins/marketplaces/my-experts/plugins/shunge-selfmedia/`
2. 在 `marketplaces/my-experts/.codebuddy-plugin/marketplace.json` 的 `plugins` 数组加一条（name / source / description / version）

推包结构：`.codebuddy-plugin/plugin.json` + `agents/` + `skills/` + `avatars/`。
