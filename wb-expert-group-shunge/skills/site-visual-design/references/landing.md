# 原型落到静态站 / WordPress

> 下文 S1/S2、sku 路径、主题/插件名称仅是历史工程的适配示例，不是当前项目默认依赖或安装指令。
> 使用前先定位当前项目真实入口，将示例路径映射到其内容源、主题、构建和测试命令；没有对应工程时不要照跑。
> 报价、页数、插件数量和品牌均按当前项目确认，不继承示例限制。

> 前提：原型已定稿（`mockup.py check` 通过 + 真浏览器点过 + 客户认可方向）。
> 这一步是把**方向**变成**能上线的站**，不是把原型文件搬过去。

## 通用前置

1. **出图的图是演示素材。** 正式交付前必须换客户原图，或在页面明确标注示例内容。
   客户以为那是他的店，就是事故。
2. **文案从客户资料来**，不从原型抄。原型里的文字是为了撑版式写的占位。
3. **先确认页数和资产范围**，按当前项目约定验收。
   原型超范围先协商，不先做。
4. **改完自检 + 真浏览器验收**，两边都要。

---

## 一、落到 S1 静态站

静态站通常无后台。以下保留原工程的模板、profile 和相册三类适配示例，不规定价格。

### 路线 A：成品模板（默认最快）

适合单页名片、服务展示、门店展示。

```
sku/S1-personal-site/engine/presets/
├── card/     单页名片
├── service/  服务展示
├── shop/     门店展示
└── album/    相册
```

做法：

```bash
# 1. 复制整个 site/ 目录（不是复制文件，是整个目录）
cp -r sku/S1-personal-site/engine/presets/card/site delivery/S1-<客户名>/site

# 2. 改文案与图片：site.js 是内容源，images/ 同名替换
#    看 engine/presets/card/README.md 确认 site.js 的字段结构

# 3. 本地预览 + 验收
python sku/S1-personal-site/album/scripts/serve.py delivery/S1-<客户名>/site 4300
cd sku/S1-personal-site/engine && node check.mjs --url http://127.0.0.1:4300/
```

**退出码 0 才算过。** 要烤进单文件用 `node sku/S1-personal-site/engine/build.mjs --site <客户目录>/site`。

S1 成品的硬要求：
- **能双击打开**（`file://` 协议下样式、图片、脚本全部正常）
- 脚本必须是 IIFE；ESM/IIFE 子页资源都要用 `../` 相对路径
- **全站搜 `{{` 一个不留**（模板占位符）
- `site.url` 换成客户真域名；电话、微信、备案号换成客户的
- 图片换成客户原图，**同名替换**

### 路线 B：Vue profile（多页、定制、演示站）

```bash
# 1. 采集单转 profile 骨架
python sku/S1-personal-site/scripts/intake_to_profile.py --input <采集单> --name <名>
#    多页加 --multi，要表单加 --booking

# 2. 改 profiles/<名>.json：文案、配色、图片路径
#    配色在 theme.primary / theme.primaryDark / theme.accent

# 3. 一键构建 + 逐页验收 + 打包
python sku/S1-personal-site/scripts/deliver_static.py --profile <名> --out delivery/S1-<客户名>/构建产物
```

`deliver_static.py` 内部会调 `check.mjs`，**失败退出 1 且不出包**。

### 路线 C：相册

```bash
python sku/S1-personal-site/album/scripts/photos.py --src <原图目录> --out <工作>/_album
python sku/S1-personal-site/album/scripts/build.py --config album.json --work <工作>/_album --out <工作>/dist
```

**构建读 `--work` 不是 `--photos`**（这是老坑）。`album/presets/` 有六套填好结构的
场景骨架（旅行/纪念/毕业/婚礼/宝宝/宠物），问清场景就 `cp` 一份填空。

三套相册主题：travel / film / grid。

### S1 改完必查

- [ ] `check.mjs` 退出码 0
- [ ] 全站搜 `{{` 无残留
- [ ] 域名、联系方式、备案号是客户的
- [ ] 图片是客户原图（或明确标注示例）
- [ ] 桌面 1440 与手机 390 各走一遍，逐页截图
- [ ] 控制台无报错、图片无 404
- [ ] 电话/微信/复制/导航按钮真能点
- [ ] 门店类：地址可见可复制、营业时间与店休日、高德导航链接、JSON-LD 的 streetAddress/areaServed/hasMap

---

## 二、落到 S2 WordPress 站

S2 是**带后台的真站**，「客户以后自己能改」是卖点。
**站型与版式正交**：站型（`--type`）决定页面骨架，版式（`style`）只决定配色排版。

| 站型 | 参数 | 页数 | 重点 |
| --- | --- | --- | --- |
| personal | `--type personal` | 4 页 | H1 是姓名，询盘表单 |
| local | `--type local` | 6 页 | 预约 |
| products | `--type products` | 6 页 | 产品参数与询盘 |
| store | `--type store` | 6 页 | 菜单管理与预约状态 |

版式：`portal` / `showcase` / `marketing` / `culture` 在 `opc-business` 主题，
`store` 在 `opc-store` 主题（门店结构固定，只换配色，共 4 套）。
**别让客户在后台「外观 → 主题」里换主题**，换到另一个主题会丢模板；
版式走「设置→站点资料」，配色走「外观 → 自定义 → 配色方案」，两处同一个值。

### 原型要素 → 改哪里

| 原型里有什么 | 改哪 | 说明 |
| --- | --- | --- |
| 配色、圆角、间距、版式感 | `engine/themes/opc-business/assets/styles/<版式>.css`；门店不是版式，改 `themes/opc-store/assets/styles/store.css` | 一套版式一个文件 |
| 换配色（不改结构） | `themes/<主题>/themes.json`，由 `scripts/store_themes.py` 生成 | 别手调色值，跑 `test_store_themes.php` 复核对比度 |
| 首屏、砖块、FAQ、CTA 的结构 | `scripts/wp_products.py` 的 `styled_home()` | 各站型分支在同文件 |
| 门店站六页骨架 | `scripts/wp_products.py` 的 `store_pages()` | |
| 图文砖 | `scripts/wp_products.py` 的 `service_tiles()` | 每块要有图、链接、alt |
| 菜单分类筛选 | `engine/plugins/opc-site-kit/includes/catalog.php` | `[opc_products filter="1"]` |
| 按钮文案 | `order.json` 的 `catalog_cta` | 门店写「看看详情」，工厂写「获取报价」 |
| 首屏实拍图 | `order.json` 的 `hero_image` | 相对 order.json 的路径 |
| 砖块图 | `order.json` 的 `services[].image` 与 `services[].link` | |

### 改配色：别在插件里硬编码

插件 `opc-site-kit` 的样式必须用**带兜底的 CSS 变量**：

```css
/* 对 */
background: var(--opc-brand, #126b5b);

/* 错——插件的样式会盖过主题，改主题颜色盖不住 */
background: #126b5b;
```

改完记得**升插件版本号**并把样式版本换成 `filemtime`（`opc-site-kit.php` 与
`includes/output.php`），否则浏览器缓存旧样式，业主会看到绿色按钮。

### 改完自检

```bash
# 1. 站型与版式（不依赖 WP 与 MySQL，直接调页面组装函数）
python sku/S2-business-site/scripts/test_site_types.py     # 退出码 0

# 2. 动了加固或本地化
php sku/S2-business-site/scripts/test_opc_harden.php       # 退出码 0

# 3. 生成部署清单（本机没 MySQL 时用离线版）
python sku/S2-business-site/scripts/wp_products_offline.py \
  --order examples/<站>/order.json --type store \
  --products examples/<站>/products.csv --domain <域名> \
  --img-dir examples/<站>/img --out <清单.json>

# 4. 浏览器验收
node sku/S2-business-site/scripts/check.mjs --url <网址> --kind wp --booking
```

`php -l` **不够**——它只证明语法对，证明不了钩子挂对。改插件逻辑必须跑桩测试。

### 上线

按 `ops-deploy`：备份 → 上传 → 属主权限 → 证书 → 伪静态 → 正式域名复验。
**上线覆盖而非先删后拷**，保留百度/必应验证文件；先备份，可回滚。

### S2 改完必查

- [ ] `test_site_types.py` 退出码 0
- [ ] 动了加固则 `test_opc_harden.php` 退出码 0
- [ ] `check.mjs --kind wp --booking` 全过
- [ ] 预约**实际提交一次**，核对后台记录出现该条（验后删掉测试记录）
- [ ] 后台能改文字、换图、改联系方式（客户自己能改才算交付）
- [ ] 插件按当前项目批准的依赖清单核验，不强制特定品牌或数量
- [ ] JSON-LD 与可见文字一致（门店与本地服务 LocalBusiness、企业 Organization、个人 Person）
- [ ] 页脚备案号链到工信部（只在真有时输出）
- [ ] 移动端 390 与微信内各看一次，无横向滚动
- [ ] 逐页截图留证

---

## 三、原型与成品允许的差异

原型是简化演示，成品必须有原型没有的东西。**这些差异是正常的，不是没对齐**：

| 原型 | 成品多了什么 |
| --- | --- |
| 表单点了出成功态 | 后台真的有记录、通知邮件真发出去 |
| 硬编码的文案 | 后台能改 |
| 静态图片 | 后台能换 |
| 没有多语言 | 后台中文、日期格式本地化 |
| 直接跳链接 | 伪静态 URL、404 页、sitemap |

反过来，**成品不能比原型少东西**。原型里有图有链接的砖块，
落到成品里不能退化成纯文字卡——那是最常见的"设计稿很好、上线很素"的原因。
