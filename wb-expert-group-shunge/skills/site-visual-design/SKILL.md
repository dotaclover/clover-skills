---
name: site-visual-design
description: 建站视觉流水线：生成整站配图、可交互HTML原型并适配静态站或WordPress；含同步兼容接口与专用异步队列、提示词模板、配色与WCAG校验、原型规格及验收清单。
agent_created: true
---

# 建站视觉流水线（出图 → 原型 → 落地）

> 下文命令在仓库根目录执行（脚本路径相对仓库根），项目输入/输出使用绝对路径。
> 本技能负责站点视觉；报价、页数与交付边界由当前项目确认，不沿用示例套餐。
> WordPress 开发可参考 `wp-dev`，浏览器验收使用当前可用工具。

## 为什么要有这条流水线

客户说「太素了」「不像我的店」时，改文字没用，改配色和配图才有用。
但**直接改线上站**是错的：改坏了没法回退，客户看不到预期，改一轮就是一轮返工。

所以固定走三段，**每段都有可验收的产物**：

```
第1段 出图        整站配图一套（首屏/菜单/砖块/环境），风格统一
   ↓
第2段 原型        可交互 HTML 多页原型，配色与交互先在这儿定死
   ↓
第3段 落地        原型改成 S1 静态站 或 S2 WordPress 站，上线验收
```

**原型是中间产物，不是交付物**。别把原型直接发给客户当"网站做好了"——
客户点的是假交互、填的表单不进后台。原型只用来确认方向。

## 三段各自的红线

| 段 | 能做 | 不能做 |
| --- | --- | --- |
| 1 出图 | 写实场景图、产品图、砖块图；叠中文；采样配色 | 让模型写中文（必糊）；一上来就批量出 20 张 |
| 2 原型 | 生成多页原型、跑通筛选与表单、校验对比度 | 直接改线上站；把原型当交付物 |
| 3 落地 | 把原型搬进 S1/S2 的既有结构 | 另起一套新主题；为客户改模板文件 |

## 第1段：出图

### 脚本

```bash
# 自检（离线，不需要 Key）
python expert/skills/site-visual-design/scripts/image_api.py self-test

# 看两家配置状态
python expert/skills/site-visual-design/scripts/image_api.py providers

# 出图计划：把「站点配图」拆成一组任务，提示词骨架已经写好
python expert/skills/site-visual-design/scripts/image_api.py plan --scene 门店

# 单张出图（默认供应商 sub）
python expert/skills/site-visual-design/scripts/image_api.py send --provider sub \
  --model gpt-image-2 --size 1024x1024 --n 1 \
  --prompt "..." --out resp.json

# 落盘并核对真实尺寸
python expert/skills/site-visual-design/scripts/image_api.py save \
  --response resp.json --out-dir out --expect-size 1024x1024

# 叠中文（模型写的中文一律糊，叠字才靠谱）
python expert/skills/site-visual-design/scripts/image_api.py overlay \
  --image out/image-01.png --text "今日手冲" --out out/hero.png
```

完整子命令表见 `references/providers.md`，提示词模板见 `references/prompts.md`。

### 两个供应商

| id | 地址 | 协议 | 用法 |
| --- | --- | --- | --- |
| `sub` | `https://sub.aicodexvip.top/v1` | OpenAI 兼容，同步 | **默认**。`gpt-image-2` / `2.5-flare` / `2.5-sunburst` |
| `rrw` | `https://api.novqiao.com` | 专用图片队列，异步 | 备用。支持询价、幂等键、回调验签、参考图上传 |

脚本保留两个供应商的协议适配，端点可用 `--base-url` 覆盖；更换端点不改变协议。
默认尊重系统代理，UA 可配置，不把历史拦截行为当成永久事实。

配置默认 `~/.site-visual-design/config.json`，也可在子命令前传 `--config <文件>`。
仅显式 `--allow-legacy-config` 才读取旧 `.aigc-image` 配置。配置含明文凭据，不入库。
输出默认拒绝覆盖；需要覆盖时在子命令前加 `--overwrite`。`build/send` 必须显式 `--out`，输入输出不能同名。
叠字通过 `--font <字体文件>` 或 `IMAGE_FONT` 配置，不依赖 Windows 字体。

### 出图四条硬规则

1. **默认 `n=1`**。一次成功就停。要追加、换模型重试，客户明确说才做。
2. **中文一律不让模型写**。小字必糊，出图后用 `overlay` 叠。
3. **一套图一个风格**。光线、色温、材质这三句抄三遍到每条提示词里。
   每张单独写提示词必然风格漂移，整站看起来像拼的。
4. **出完核对尺寸**。`save --expect-size` 会标 `size_mismatch`。
   尺寸限制随供应商和模型变化，不能将历史上限作为永久事实。

## 第2段：原型

### 为什么用规格 JSON 而不是直接写 HTML

手写六页 HTML，改一次导航要动六个文件，配色改一次要全局搜。
规格 JSON 是唯一事实源，改规格重新生成，页面之间不会走样。

### 三条命令

```bash
# 从规格生成多页可交互原型（HTML+CSS+JS，无构建无依赖）
python expert/skills/site-visual-design/scripts/mockup.py scaffold \
  --spec spec.json --out proto/ --img-dir 出图目录/

# 从设计图采样主色，算 WCAG 对比度
python expert/skills/site-visual-design/scripts/mockup.py palette \
  --image 设计稿.png --paper "#fbf7f1"

# 体检：资源缺失、占位符残留、对比度不达标、每页 H1 数量
python expert/skills/site-visual-design/scripts/mockup.py check --dir proto/
```

**规格 JSON 的字段与区块类型见 `references/mockup-spec.md`**，
可直接抄的门店站示例在 `examples/spec-store.json`——照那个结构改
`name`／`nav`／`palette`／`pages` 就行，不用从零想结构。

### 原型的验收口径

`check` 过 ≠ 验收过。**必须在真浏览器里点一遍**：

- 六页都能打开，无 404、无 console 报错
- 菜单分类筛选真的能筛（点胶囊，看卡片数量变化）
- 表单空提交被拦、填完出成功态
- 手机 390 视口无横向溢出，汉堡能展开导航
- 每个页面**有且只有一个 H1**，标题不重复出现两遍

参考 `computer-use` 等当前可用浏览器工具；先探测依赖，不假定本机已有 Edge 或 puppeteer-core。

### 配色怎么定

- 正文 4.5:1、大字 3:1（WCAG AA）。`check` 会算，不达标会报。
- **主色按钮底色配白字最容易踩线**。实测设计稿里的 `#a56537` 是 4.65:1，
  刚过线；压到 `#a05f30` 有 5.03:1，留余量，肉眼几乎看不出差别。
  `scaffold` 发现不达标会**自动压深并在报告里写明**。
- 深浅两套底都要试：门店站暖底配深棕字，个人站白底配深蓝字。

## 第3段：落地

原型定稿后，按站型落到既有结构里。**不要另起一套新主题。**

### 落到 S1 静态站

静态站通常无后台。下列 S1/S2 路径仅保留为历史工程适配示例，先映射当前项目入口，不假定存在该 SKU、价格、主题或插件。

| 原型形态 | 落到哪 | 怎么改 |
| --- | --- | --- |
| 单页名片/服务/门店 | `sku/S1-personal-site/engine/presets/<card\|service\|shop>/site/` | 复制整个 `site/` 目录 → 改 `site.js` 与 `images/` 同名替换 |
| 多页 | `sku/S1-personal-site/engine/` + `profiles/<名>.json` | 改 profile 的 `theme`（primary/accent）与文案。相册版式已停售，不再有相册路线 |

改完的验收：

```bash
python sku/S1-personal-site/scripts/serve.py <客户目录>/site 4300
cd sku/S1-personal-site/engine && node check.mjs --url http://127.0.0.1:4300/
```

**退出码 0 才算过。** S1 成品必须是能双击打开的文件夹：`file://` 协议下
脚本必须是 IIFE，子页资源用 `../` 相对路径。

### 落到 S2 WordPress 站

S2 是带后台的真站，**版式与站型正交**：站型（`--type`）决定页面骨架，
版式（`style` 字段）只决定配色排版。原型一般落在某个既有版式上。

| 要改什么 | 改哪 | 注意 |
| --- | --- | --- |
| 配色 | `engine/themes/<主题>/themes.json`（由 `sku/S2-business-site/scripts/store_themes.py` 生成），版式 CSS 在 `assets/styles/<版式>.css` | 别手调色值，改完跑 `test_store_themes.php`；插件里用 `var(--opc-*)` 带兜底 |
| 页面骨架 | `sku/S2-business-site/scripts/wp_products.py` 的 `styled_home()` / 各站型分支 | 改完跑 `python sku/S2-business-site/scripts/test_site_types.py` |
| 砖块图文 | `sku/S2-business-site/scripts/wp_products.py` 的 `service_tiles()` | 每块砖必须有图、有链接、有 alt |
| 菜单筛选 | `engine/plugins/opc-site-kit/includes/catalog.php` | `[opc_products]` 的 `filter` 属性 |
| 按钮文案 | `order.json` 的 `catalog_cta` | 门店站写「看看详情」，工厂站写「获取报价」 |

改完的验收：

```bash
python sku/S2-business-site/scripts/test_site_types.py    # 退出码 0
php sku/S2-business-site/scripts/test_opc_harden.php      # 动了加固就跑
node sku/S2-business-site/scripts/check.mjs --url <网址> --kind wp --booking
```

**加插件必须同步两处硬编码**：`sku/S2-business-site/scripts/wp_local.py` 的 `PLUGINS` 与
`sku/S2-business-site/scripts/server_deploy_wp.sh` 的 `plugin activate`，不同步就建站不装、上线不启用。

### 落地后必查

- 全站搜 `{{` 一个不留（占位符残留）
- `site.url` 换成客户真域名；电话、微信、备案号换成客户的
- 图片换成客户原图（出图的图是**演示素材**，正式交付前必须换掉或标注示例）
- 手机 390 与桌面 1440 两个视口各走一遍，**逐页留截图**
- 预约/询盘表单**实际提交一次**，核对后台记录出现

## 红线

1. **出图的图是演示素材。** 正式交付前换客户原图，或在页面明确标注示例内容。
   不要让客户以为那是他的店。
2. **原型不是交付物。** 客户要的是能用的站，不是能点的假页面。
3. **不承诺 AI 图的效果。** 出图是辅助，页面的骨架、信息层级、可访问性
   才是站能不能用的关键。
4. **不擅自加页。** 页数、资产量和交付边界按当前项目约定；超范围先确认。
5. **改配色要算对比度。** 看着舒服不等于达标，AA 是底线。
6. **客户提供的照片版权客户自负。** 不修图、不调色、来路不明的图不放。

## 目录

```
site-visual-design/
├── SKILL.md
├── scripts/
│   ├── image_api.py         出图（两个供应商）+ 叠字 + 计划
│   └── mockup.py            出原型 + 采配色 + 体检
├── examples/
│   └── spec-store.json      门店站原型规格示例，照着改
└── references/
    ├── prompts.md            全部提示词模板（出图、原型、叠字）
    ├── providers.md          两个供应商的接口细节与坑
    ├── mockup-spec.md        规格 JSON 字段与区块类型
    └── landing.md            原型落到 S1/S2 的具体改法
```
