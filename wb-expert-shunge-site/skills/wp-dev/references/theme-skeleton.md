# 主题骨架与模板层级

> 以下`site-business`/`site-store`仅为经典主题结构示例，不要求安装固定仓库；先映射到当前主题目录与测试工具，参数及实现以现场代码为准。

**一个主题一个结构立场。** 门店站（首屏大图、招牌砖、到店信息、菜单、在线订位）与企业站不是一路，硬塞进同一套模板只会四不像，所以拆成两个主题：`site-business` 管四套版式，`site-store` 结构写死、只换配色。加新站型前先问一句「骨架是不是真的一样」，不一样就开新主题，别在模板里堆 `if`。

## 一、目录

```
themes/site-business/       # 产品站：四套版式
  style.css                 主题头（必需）+ 变量与基础样式
  functions.php             只放 theme_support、菜单、enqueue
  themes.php                配色读取 + 内联变量覆盖（require 同目录 themes.json）
  themes.json               配色表：单一事实源，JSON 由 sku/S2-business-site/scripts/store_themes.py 生成
  screenshot.png            后台主题页封面，1200×900，缺了就是灰格子
  header.php                开标签到主内容开始
  footer.php                页脚 + wp_footer
  index.php                 兜底模板，必须有
  page.php                  普通页面
  page-landing.php          落地页（长页、无侧栏）
  single.php                文章详情
  archive-site_product.php   产品列表（CPT 归档）
  single-site_product.php    产品详情
  taxonomy-site_product_category.php  产品分类
  patterns/                 区块样板，后台插入即用
    a1-personal.php
    local-service.php
    product-showcase.php
  assets/
    app.js
    styles/portal.css showcase.css marketing.css culture.css
  theme.json                只管编辑器的间距与字号档位

themes/site-store/          # 门店站：结构写死，只换配色
  （同上骨架，assets/styles 只有 store.css，themes.json 是 4 套配色）
```

**没有 `front-page.php` 是有意的**：首页由后台「设置→阅读」指定一个页面，比在主题里写死首页内容好维护——客户换首页不用找人改代码。

## 二、style.css 必需的头

```css
/*
Theme Name: 企业站主题
Theme URI: https://example.com/
Author: clover
Description: 企业与产品站专用主题。四套版式：门户信息型、现代展示型、营销转化型、中式文化型。版式在「设置 → 站点资料」里选，配色点「自定义」在「外观 → 自定义 → 配色方案」里选。
Version: 1.0.0
Requires at least: 6.5
Requires PHP: 7.4
Text Domain: clover
*/
```

`Text Domain` 要和目录名一致，否则翻译串对不上。**Description 会显示在后台主题卡片上**，写清「什么时候选这个主题」，别写「五套配色」这种会过期的细节。

## 三、functions.php 的完整写法

```php
<?php
/** 主题引导：只挂主题支持、菜单与前台资源。业务逻辑不放在这里。 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

define( 'THEME_VERSION', '1.0.0' );

add_action(
	'after_setup_theme',
	static function (): void {
		add_theme_support( 'title-tag' );
		add_theme_support( 'post-thumbnails' );
		add_theme_support( 'html5', array( 'search-form', 'comment-form', 'comment-list', 'gallery', 'caption', 'style', 'script' ) );

		register_nav_menus(
			array(
				'primary' => '主导航',
				'footer'  => '页脚导航',
			)
		);
	}
);

add_action(
	'wp_enqueue_scripts',
	static function (): void {
		// 版本号用常量：改样式后客户看到旧样子，多半是缓存拿的是同一个版本号。
		wp_enqueue_style( 'site-theme', get_stylesheet_uri(), array(), THEME_VERSION );

		$style = (string) get_option( 'site_site_style', 'portal' );
		if ( 'portal' !== $style ) {
			wp_enqueue_style(
				'site-site-' . $style,
				get_theme_file_uri( 'assets/styles/' . $style . '.css' ),
				array( 'site-theme' ),
				THEME_VERSION
			);
		}

		wp_enqueue_script( 'site-theme', get_theme_file_uri( 'assets/app.js' ), array(), THEME_VERSION, true );
	}
);
```

内联脚本用 `wp_add_inline_script()` 挂在已注册的 handle 后面，不要往 `header.php` 里写 `<script>`。样例实现参照当前工作区已有代码，未提供的历史备份不作为依赖。

## 四、header.php 不能少的三行

```php
<!DOCTYPE html>
<html <?php language_attributes(); ?>>
<head>
<meta charset="<?php bloginfo( 'charset' ); ?>">
<meta name="viewport" content="width=device-width, initial-scale=1">
<?php wp_head(); ?>
</head>
<body <?php body_class(); ?>>
<?php wp_body_open(); ?>
<a class="skip-link" href="#main">跳到正文</a>
```

- `wp_head()`、`wp_body_open()`、`wp_footer()` 三个一个都不能漏。漏 `wp_head()` 插件全失效，漏 `wp_body_open()` 统计代码挂不上，漏 `wp_footer()` 表单脚本不加载。
- 不要在 `<head>` 里手写 `title`、`description`、`og:` 标签——`title-tag` 支持已接管标题，站点描述与 og 由 SEO 插件或 `godance-core` 那种类输出，重复输出会出现两组 meta。
- 跳转链接（skip link）是无障碍底线，样式里默认移出屏幕、聚焦时出现在左上。

## 五、模板层级

WordPress 按这个顺序找模板，找到第一个就用，后面的不再看：

| 页面类型 | 查找顺序 |
| --- | --- |
| 首页（指定了静态页） | `front-page.php` → `page.php` → `singular.php` → `index.php` |
| 普通页面 | 自定义模板 → `page-{slug}.php` → `page-{id}.php` → `page.php` → `singular.php` → `index.php` |
| 文章详情 | `single-{post_type}.php` → `single.php` → `singular.php` → `index.php` |
| 归档列表 | `archive-{post_type}.php` → `archive.php` → `index.php` |
| 分类法 | `taxonomy-{tax}-{term}.php` → `taxonomy-{tax}.php` → `archive.php` → `index.php` |
| 搜索结果 | `search.php` → `index.php` |
| 404 | `404.php` → `index.php` |

六页站只用得上 `page.php` 与 `page-landing.php`。**不要为每一页建一个模板文件**：六个模板意味着改页脚要改六处，第二个客户就维护不动了。

落地页用「页面属性→模板」选，不用 slug 硬编码：

```php
<?php
/**
 * Template Name: 落地页
 */
```

## 六、patterns 的写法

样板是一段注册到后台的区块组合，客户插入后能直接改文字。文件头的字段决定它在插入面板里叫什么：

```php
<?php
/**
 * Title: 本地服务首页
 * Slug: site-site/local-service
 * Categories: site-pages
 * Description: 首屏、服务项、案例、常见问题、联系。
 */
?>

<!-- wp:group {"className":"site-hero"} -->
<div class="wp-block-group site-hero">
	<!-- wp:heading {"level":1} -->
	<h1 class="wp-block-heading">替客户写一句具体的首屏</h1>
	<!-- /wp:heading -->
</div>
<!-- /wp:group -->
```

样板里的文案必须是可以直接交付的真话，不能留「示例标题」——客户点一下就上线了。

## 七、theme.json 只做一件事

给区块编辑器一组受控的间距与字号，避免客户调出 13 种字号。**不要**在这里接管颜色与排版，那会和 `style.css` 打架，出问题时不知道改哪边生效。

```json
{
	"$schema": "https://schemas.wp.org/trunk/theme.json",
	"version": 3,
	"settings": {
		"spacing": { "units": [ "px", "rem" ] },
		"typography": { "fluid": false }
	}
}
```

## 八、配色：变量覆盖，不复制 CSS

配色分两层，别混：

**结构层**——版式 CSS 在 `assets/styles/<版式>.css` 里给 `.site-style-<版式>` 定义一套变量（`--site-paper`、`--site-brand`、`--site-ink`…），`<body>` 上带 `site-style-portal` 这类类名（由 `site_style()` 读站点资料决定）。

**配色层**——每套配色只是同一组变量换值，存在 `themes.json`：

```json
[{ "id": "navy", "name": "深蓝", "desc": "工业、制造", "vars": { "--site-brand": "#1a4b8c", "--site-paper": "#ffffff" } }]
```

由 `themes.php` 的 `site_theme_inline_style()` 用 `wp_add_inline_style()` 追加一条 `.site-style-portal{…}`，优先级等于版式 CSS、加载在其后，所以只覆盖颜色不动布局。**变量声明在 body 上，不在 `:root`**——这样作用域收在页面里，不会污染后台工具栏；排查颜色时读 `getComputedStyle(document.body)`，读 `documentElement` 拿到的是基础层默认值，会误判成「没生效」。

规矩：
- 加一套配色 = 改 `themes.json`（用 项目内的配色表脚本 算，连同对比度一起解），不写新 CSS、不动 PHP。
- 每套都要过 WCAG AA：正文对纸底 ≥4.5:1，按钮白字 ≥4.5:1，描边 ≥3:1。手调色值迟早翻车，跑当前项目已核实的配色对比度测试；缺少工具时逐项检查并记录结果。
- 客户换配色走「外观 → 自定义 → 配色方案」（`site-site-kit` 注册的色块控件）或「设置 → 站点资料 → 配色主题」，两处读写**同一个 option 键**（`site_site_kit[theme]`），不要另存一份。

## 九、常见错误

| 现象 | 原因 |
| --- | --- |
| 后台改的标题不生效 | `header.php` 里手写了 `<title>`，`title-tag` 支持被顶掉 |
| 插件全不工作 | 漏了 `wp_head()` 或 `wp_footer()` |
| 改了 CSS 客户看不到 | enqueue 的版本号写死，缓存拿的旧文件 |
| 表单提交没反应 | 主题里 dequeue 了业务插件的前端脚本 |
| 编辑器里作者选择报错 | 安全插件把 `/wp/v2/users` 对已登录用户也摘了 |
| 中文文件名上传后 404 | 上传时没走 `sanitize_file_name`，URL 被转义 |
| 样板插入后样式全乱 | 样板里用了主题没定义的类名，或者带了内联 style |
| 后台主题页显示成灰格子 | 主题目录缺 `screenshot.png`，或尺寸不是 1200×900（会被拉伸） |
| 自定义器里自定义控件整段不显示 | 控件类写在插件顶层 `extends WP_Customize_Control`，插件加载时该类还不存在 → 类定义不出来 → `add_control` 撞未定义类，整个 `customize_register` 中断。类要单独一个文件，在钩子回调里 `require_once` |
