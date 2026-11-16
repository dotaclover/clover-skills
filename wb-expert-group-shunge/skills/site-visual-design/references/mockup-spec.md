# 原型规格 JSON

`mockup.py scaffold --spec spec.json --out proto/ --img-dir 出图目录/`

规格是原型的唯一事实源。改设计改规格重新生成，**别手改产物**。

## 顶层字段

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `name` | 是 | 站名。用于标题、页脚、字标方块首字 |
| `kicker` | 否 | 小标签，一般放在 H1 上方 |
| `lead` | 否 | 一句话介绍，放页脚 |
| `description` | 否 | meta description |
| `nav` | 是 | 导航项数组：`{"label": "首页", "href": "index.html"}` |
| `navCta` | 否 | 导航右侧按钮：`{"label": "在线订位", "href": "booking.html"}` |
| `palette` | 否 | 配色，见下 |
| `footer` | 否 | 页脚栏目数组：`{"title": "站点", "items": [{"label","href"}]}` |
| `footNote` | 否 | 页脚左侧小字（如"本站为演示站"） |
| `copyright` | 否 | 页脚右侧版权 |
| `pages` | 是 | 页面数组 |

## 配色

```json
"palette": {
  "paper":   "#fbf7f1",
  "paper2":  "#f3ece0",
  "ink":     "#7c4724",
  "body":    "#6f5f50",
  "soft":    "#7a6a5b",
  "line":    "#e8ddcd",
  "brand":   "#a56537",
  "onbrand": "#fffdfa"
}
```

| 键 | 用途 | 缺省 |
| --- | --- | --- |
| `paper` | 页面底色 | `#fbf7f1` |
| `paper2` | 交替区块底色 | `#f3ece0` |
| `ink` | 标题色 | `#2b2622` |
| `body` | 正文色 | `#4a423a` |
| `soft` | 次要信息色 | `#7a6a5b` |
| `line` | 分隔线与描边 | `#e8ddcd` |
| `brand` | 主色（按钮底、强调） | `#a05f30` |
| `onbrand` | 主色上的文字色 | `#fffdfa` |

**`brand` 对 `onbrand` 的对比度不足 4.5:1 时，scaffold 会自动压深主色**
并在报告里写明改动前后对比度。深浅底都建议试一遍。

## 页面

```json
{
  "slug": "index",
  "title": "首页",
  "blocks": [ ... ]
}
```

`slug` 为 `index` 时输出 `index.html`，其余为 `<slug>.html`。
`blocks` 的顺序就是页面上的顺序。

**标题层级规则**：页面第一个带 `title` 的区块渲染成 H1，其后的都是 H2。
一个页面有且只有一个 H1，标题不会重复出现两遍。

## 区块类型

### hero — 首屏

```json
{
  "type": "hero",
  "kicker": "江南西 · 手冲咖啡",
  "title": "街角的豆子，慢慢冲",
  "lede": "两到三句：卖什么、什么氛围、怎么来",
  "facts": ["手冲豆单每周换一次", "面包每天烤两炉"],
  "actions": [
    {"label": "看看菜单", "href": "menu.html", "primary": true},
    {"label": "在线订位", "href": "booking.html"}
  ],
  "image": "img/store-gate.jpg",
  "alt": "门店门头",
  "badge": "营业中"
}
```

- `actions` 里 `primary: true` 的用实心按钮，其余描边
- `image` 建议 4:5 竖构图（CSS 按 `aspect-ratio: 4/5` 裁）
- `badge` 叠在图左下角（如"营业中"）
- `facts` 渲染成胶囊标签

### tiles — 图文砖

```json
{
  "type": "tiles",
  "title": "招牌与主营",
  "lead": "可选副标题",
  "items": [
    {"img": "img/tile-pour.jpg", "title": "手冲咖啡", "text": "每周换豆单", "href": "menu.html", "more": "看详情"}
  ]
}
```

桌面 4 列、平板 2 列、手机 1 列。**每块必须有图、有链接**——
没有图的砖等于占着黄金位置不干活。

### menu — 菜单列表

```json
{
  "type": "menu",
  "title": "菜单与产品",
  "lead": "价格为门店当日价",
  "categories": ["全部", "手冲", "意式", "甜点"],
  "items": [
    {"img": "img/m1.jpg", "name": "耶加雪菲", "desc": "浅烘，柑橘与花香", "price": "38", "cat": "手冲"}
  ]
}
```

- `categories` 第一项是"全部"，其余要与 `items[].cat` 对得上
- 图左文右横排卡，一屏两列
- 筛选是纯前端，点胶囊切换，无 JS 时全部可见

### info — 信息卡

```json
{
  "type": "info",
  "title": "到店信息",
  "items": [
    {"label": "地址", "value": "示例市示例路 88 号（虚构，不可用于导航）"},
    {"label": "营业时间", "value": "每天 08:00—20:00"}
  ]
}
```

桌面 3 列。门店站的地址、营业时间、联系方式放这里。

### figures — 数字条

```json
{"type": "figures", "title": "可选", "items": [{"num": "18", "label": "个座位"}]}
```

### faq — 常见问题

```json
{
  "type": "faq",
  "title": "常见问题",
  "items": [{"q": "需要提前订位吗", "a": "周末人多，建议提前一天订。"}],
  "moreHref": "booking.html",
  "moreText": "在线订位"
}
```

用原生 `<details>`，无 JS 也能展开。

### form — 表单

```json
{
  "type": "form",
  "title": "在线订位",
  "lead": "可选",
  "note": "提交后不是即时确认，店员会联系您确认。",
  "consent": "同意店家通过电话或微信与我联系",
  "submit": "提交预约",
  "fields": [
    {"name": "customer_name", "label": "怎么称呼您", "type": "text", "required": true},
    {"name": "phone", "label": "联系电话", "type": "tel", "required": true},
    {"name": "service", "label": "预约类型", "type": "select", "options": ["订位 2 人", "订位 4 人"]},
    {"name": "note", "label": "备注（选填）", "type": "textarea"}
  ]
}
```

- `type` 支持 `text` / `tel` / `email` / `number` / `select` / `textarea`
- 空的 `required` 字段提交会被拦并标红
- `consent` 不为空时自动加一个同意勾选框

### cta — 行动号召

```json
{"type": "cta", "title": "周末人多，先订个位", "text": "订位不收订金。", "button": {"label": "在线订位", "href": "booking.html"}}
```

### prose — 图文段落

```json
{"type": "prose", "title": "关于我们", "paragraphs": ["第一段。", "第二段。"]}
```

### pagehead — 手动页头

```json
{"type": "pagehead", "title": "页面标题", "lead": "可选副标题"}
```

一般用不上：区块自带标题时会自动升级成 H1。

## 输出的文件

```
proto/
├── index.html
├── <其他页>.html
├── style.css     自动生成，勿手改
├── app.js        自动生成，勿手改
└── img/          从 --img-dir 拷进来的图
```

`style.css` 与 `app.js` 是脚本生成的，**改设计改规格 JSON**。
真要改交互逻辑，改 `mockup.py` 里的 `CSS_TEMPLATE` / `JS_TEMPLATE`。

## 体检

```bash
python scripts/mockup.py check --dir proto/
```

查这些：
- 资源引用是否都存在（图片名拼错会被抓出来）
- 有没有 `{{` `【` `TODO` 残留
- 三个关键对比度（brand/白字、ink/底色、body/底色）达不达 AA
- 每页 H1 数量（0 个或多个都报）
- 有没有 viewport meta、有没有 title

**check 过 ≠ 验收过。** 还要在真浏览器里点一遍筛选与表单，截桌面与手机两套图。
