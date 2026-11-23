# 顺哥专家团上架计划（2026-11-23）

9 个单专家 + 9 个独立技能，全部按 WorkBuddy 专家包 / Skill 规范落在 `clover-skills/`。本文记录每个包的来源、改了什么、还差什么，避免下次重新判断。

## 一、专家（9 个，均为 Agent 型单专家）

| 展示名 | 标识 / 目录 | 分类 | 内置技能 | 来源 | 状态 |
|---|---|---|---|---|---|
| 小红书运营顺哥 | `shunge-xhs` / `wb-expert-shunge-xhs` | 05 营销增长 | wb-skill-xhs-copy、copy-proof | 新写 Agent + 迁移技能 | 可上架 |
| 视频号运营顺哥 | `shunge-channels` / `wb-expert-shunge-channels` | 05 营销增长 | wb-skill-channels-copy、copy-proof | 新写 Agent + 迁移技能 | 可上架 |
| 抖音运营顺哥 | `shunge-douyin` / `wb-expert-shunge-douyin` | 05 营销增长 | wb-skill-douyin-copy、douyin-trending、copy-proof | 新写 Agent + 迁移技能 | 可上架 |
| 快手运营顺哥 | `shunge-kuaishou` / `wb-expert-shunge-kuaishou` | 05 营销增长 | wb-skill-kuaishou-copy、copy-proof | 新写 Agent + 迁移技能 | 可上架 |
| 短剧专家顺哥 | `shunge-drama` / `wb-expert-shunge-drama` | 06 内容创作 | short-drama、wb-skill-storyboard、seedance-dev、doubao-web-video、doubao-web-image | 复用 1.1.0，升 1.2.0 | 可上架 |
| 独立站专家顺哥 | `shunge-site` / `wb-expert-shunge-site` | 02 技术工程 | site-delivery、site-launch、site-audit、site-maintenance、wp-dev、wp-admin | 新写 Agent + 迁移技能 | 可上架 |
| 网页RPA专家顺哥 | `shunge-rpa` / `wb-expert-shunge-rpa` | 02 技术工程 | wb-skill-web-rpa（新写）、computer-use | 新写 Agent + 新写技能 | 可上架 |
| 网站SEO专家顺哥 | `shunge-seo` / `wb-expert-shunge-seo` | 05 营销增长 | wb-skill-seo | 新写 Agent + 迁移并自包含 | 可上架 |
| 网站GEO专家顺哥 | `shunge-geo` / `wb-expert-shunge-geo` | 05 营销增长 | wb-skill-geo、wb-skill-seo | 新写 Agent + 迁移并自包含 | 可上架 |

- 头像统一为 `expert/avatars/guangzhou-shunge.png`（371KB，≤500KB），各包各存一份，文件名跟随 agent id。
- 短剧不新建目录：`shunge-drama` 已是宿主注册名，新开同名包会注册不进去。只把头像换成统一的，并补齐 3 条推荐提示词、把描述压到 42 字。

## 二、技能（9 个独立包）

| 展示名 | 标识 / 目录 | 来源 | 改动 | 状态 |
|---|---|---|---|---|
| 顺哥小红书文案助手 | `wb-skill-xhs-copy` | `xhs-note-studio` | 改名、改显示名 | 直接迁移 |
| 顺哥视频号文案助手 | `wb-skill-channels-copy` | `wxchannels-script-studio` | 改名、改显示名 | 直接迁移 |
| 顺哥抖音文案助手 | `wb-skill-douyin-copy` | `douyin-script-studio` | 改名、改显示名 | 直接迁移 |
| 顺哥快手文案助手 | `wb-skill-kuaishou-copy` | `kuaishou-script-studio` | 改名、改显示名 | 直接迁移 |
| 顺哥网站SEO助手 | `wb-skill-seo` | `seo` | 自包含：内联交付规程 | 需补链接（已补） |
| 顺哥网站GEO助手 | `wb-skill-geo` | `geo` | 自包含：内联 SEO 地基 + 交付规程 | 需补链接（已补） |
| 顺哥网页RPA助手 | `wb-skill-web-rpa` | 无 | 全新编写 + 验收清单 | 新开发 |
| 顺哥豆包图片助手 | `wb-skill-doubao-image` | `doubao-web-image` | 改名、改显示名 | 直接迁移 |
| 顺哥豆包视频助手 | `wb-skill-doubao-video` | `doubao-web-video` | 改名、改显示名 | 直接迁移 |

## 三、三档结论

**① 脱敏后可直接迁移（4 个内容技能 + 2 个豆包技能）**

四个平台文案技能本来就是零预设写法，不含垂类、人群、客户和账号数据，只改了技能名与显示名。豆包两个技能原文已明确"不依赖私人脚本、不照抄账号结论"，可直接发布；注意它们依赖用户自己已登录的浏览器，属于宿主能力，不要写成开箱即用。

**② 要重新整理才能独立（SEO / GEO）**

两个技能原来是私有包里的兄弟技能，靠 `../site-promotion/SKILL.md`、`../seo/SKILL.md` 互相引用，单独拷走会断链。已改为自包含：

- `wb-skill-seo/references/delivery-rules.md`：交付规程副本；
- `wb-skill-geo/references/seo-foundation.md` + `delivery-rules.md`：SEO 地基与交付规程副本。

**③ 要重新总结开发（网页RPA）**

原来的 `computer-use` 只是桌面/浏览器控制手册，没有 RPA 的方法论。新写 `wb-skill-web-rpa`，覆盖：开工六项契约、定位优先级（语义 > 属性 > 结构 > 文本 > 坐标）、条件等待、幂等、断点续跑、限速退避、采集与写入专项、下载认领、验收清单。这是本次唯一从零写的技能。

## 四、暂不纳入上架的三项

| 项 | 原因 | 处理建议 |
|---|---|---|
| `site-visual-design`（建站出图+原型） | `scripts/image_api.py` 写死了私有出图接口 `sub.aicodexvip.top` 与供应商配置 | 抽出通用 provider 层、去掉私有端点后再上；本次独立站专家未内置 |
| `douyin-pip-shorts`（竖屏画中画二创） | 方法涉及搬运他人素材做二创，公开上架有版权与平台合规风险 | 改写为"只处理自有授权素材"再评估 |
| `wb-expert-selfmedia` / `wb-expert-shunge-selfmedia` / `media-creator` | 与新的四个平台专家、短剧专家能力重叠，同时上架会出现多个"自媒体专家" | 新包上架后下架旧包；短剧另有一个 `shunge-ai-short-drama` 也是重复注册名，建议只保留 `shunge-drama` |

## 五、上架前待确认

1. **短剧只能留一个注册名**：仓库里现有 `shunge-drama`（本次升级）和 `shunge-ai-short-drama` 两个短剧包，注册名不同但展示名都叫短剧专家，必须下架一个。
2. **四个平台专家的"账号卡"从哪来**：技能按零预设运行，专家会在开工时问账号卡；如果希望开箱即用，需要再给每个平台做一份空白账号卡模板。
3. **独立站专家不含报价**：符合"不内置价目表"的约定，客户问价时由主理人给，专家只谈范围与交付。
4. **分类集中**：6 个包落在 05 营销增长，市场列表里可能显得同质；如果需要区分，SEO/GEO 可改 02 技术工程（与独立站同组）。

## 六、校验记录

- 8 个新专家包 + 短剧包：`validate_expert.py` 全部通过（在临时专家目录中校验，未写入宿主真实专家目录）。
- 9 个技能包：顶层条目仅 `SKILL.md` / `references` / `scripts`，目录名与 frontmatter `name` 一致，无 `[TODO]`，包内相对链接全部可达。
- 脱敏扫描：新包内无客户名、内部人名、私有仓库路径、`opc-` 内部命名、密钥；`微信号` 仅出现在"脱敏规则表"的字段名里，不是真实号码。
