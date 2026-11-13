# 插件骨架与拆分

> 下文`opc-*`仅为命名和结构示例，先映射当前项目目录、命名空间及版本要求，不依赖固定插件库存。

## 一、主文件只做三件事

```php
<?php
/**
 * Plugin Name: OPC XXX
 * Description: 一句话说清它管什么，写给人看，不写营销词。
 * Version: 0.1.0
 * Requires at least: 6.5
 * Requires PHP: 7.4
 * Author: clover-opc
 * License: GPL-2.0-or-later
 * Text Domain: opc-xxx
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

define( 'OPC_XXX_VERSION', '0.1.0' );

require_once __DIR__ . '/includes/a.php';
require_once __DIR__ . '/includes/b.php';
```

主文件里**不要**写 `add_action`。写进去以后，改任何一处逻辑都要在几百行里找钩子，而且没法单独关掉某一项。

## 二、拆分原则：一个文件一件事

判断标准很简单——**这个文件能不能用一句话说清它管什么**。说不清就拆。

```
plugins/opc-xxx/
  opc-xxx.php              头 + 常量 + require
  includes/security.php    「安全加固那几项」
  includes/locale.php      「后台语言」
  includes/catalog.php     「产品目录这个 CPT 和它的列表页」
  assets/admin.css         后台样式
  assets/front.js          前台脚本
```

反面例子：把所有钩子塞进一个 `includes/functions.php`。那样看起来整齐，实际是「第二个文件叫 functions，后面所有东西都往里加」。

## 三、命名

| 对象 | 写法 | 例子 |
| --- | --- | --- |
| 函数 | `opc_xxx_` + 动词 | `opc_harden_client_ip()` |
| 常量 | `OPC_XXX_` | `OPC_HARDEN_LOGIN_MAX` |
| 设置项 option | `opc_xxx_` | `opc_china_icp` |
| 短代码 | `opc_xxx` | `[opc_inquiry]` |
| 钩子自定义 | `opc_xxx_` | `opc_harden_client_ip` 过滤器 |

不要用 `wp_`、`init`、`theme_` 这类会被别人撞的前缀。撞了以后报的错在别人的插件里，查半天。

## 四、开关：用常量，不改代码

需要能临时关掉的项，写成一个可覆盖的常量，默认开：

```php
if ( ! defined( 'OPC_HARDEN_XMLRPC' ) ) {
	define( 'OPC_HARDEN_XMLRPC', true );
}
```

客户或接手的人在 `wp-config.php` 里 `define( 'OPC_HARDEN_XMLRPC', false );` 就关掉了，不用改插件、不用我们到场。这比在后台做一排开关省事得多，也不会被误点。

文件里相应位置开头：

```php
if ( ! OPC_HARDEN_XMLRPC ) {
	return;
}
```

## 五、设置项

往「设置→常规」加字段，用 `register_setting` 而不是自己写表单提交：

```php
add_action(
	'admin_init',
	static function (): void {
		register_setting(
			'general',
			'opc_china_icp',
			array(
				'type'              => 'string',
				'sanitize_callback' => 'sanitize_text_field',
				'default'           => '',
			)
		);

		add_settings_field(
			'opc_china_icp',
			'ICP 备案号',
			static function (): void {
				printf(
					'<input type="text" class="regular-text" name="opc_china_icp" value="%s">',
					esc_attr( (string) get_option( 'opc_china_icp' ) )
				);
			},
			'general'
		);
	}
);
```

`sanitize_callback` 不能省。省了就是存什么进什么，后台一个引号能把页面结构打破。

## 六、加一类内容（CPT）

```php
add_action(
	'init',
	static function (): void {
		register_post_type(
			'opc_product',
			array(
				'labels'       => array(
					'name'          => '产品',
					'singular_name' => '产品',
				),
				'public'       => true,
				'has_archive'  => true,
				// 不开 show_in_rest 的话，区块编辑器里改不了这类内容。
				'show_in_rest' => true,
				'menu_icon'    => 'dashicons-products',
				'supports'     => array( 'title', 'editor', 'thumbnail', 'excerpt' ),
				'rewrite'      => array( 'slug' => 'products' ),
			)
		);

		register_taxonomy(
			'opc_product_category',
			'opc_product',
			array(
				'labels'            => array( 'name' => '产品分类' ),
				'hierarchical'      => true,
				'public'            => true,
				'show_in_rest'      => true,
				'show_admin_column' => true,
			)
		);
	}
);
```

CPT 注册完记得去「设置→固定链接」点一次保存，重写规则才会刷新；代码里也可以用 `flush_rewrite_rules()`，但**只在激活钩子里调一次**，每次请求调会把站点拖死。

`show_admin_column => true` 让客户在列表页一眼看到分类，这个细节比多写十个配置项有用。

## 七、短代码

短代码输出一律先缓冲，再返回，不要直接 `echo`——直接输出会让内容跑到页面顶部：

```php
add_shortcode(
	'opc_inquiry',
	static function (): string {
		ob_start();
		?>
		<form class="opc-inquiry" method="post">
			<input type="hidden" name="opc_inquiry_nonce" value="<?php echo esc_attr( wp_create_nonce( 'opc_inquiry' ) ); ?>">
			<input type="text" name="opc_name" required>
			<button type="submit">提交</button>
		</form>
		<?php
		return (string) ob_get_clean();
	}
);
```

表单处理三件事：`wp_verify_nonce` 校验、字段逐个 `sanitize_*`、结果用 `wp_safe_redirect` 带参数回跳（不要 `wp_redirect`，会跳到站外）。

## 八、类的写法：什么时候该用类

静态方法类适合**有一组相关逻辑、要共享常量**的场景。参考站的两个类是这个模式：

```php
class OPC_Payment_Router {
	const CHINA_ONLY = array( 'alipay' );

	public static function init(): void {
		add_filter( 'woocommerce_available_payment_gateways', array( __CLASS__, 'route' ), 20 );
	}

	public static function route( $gateways ) {
		if ( is_admin() ) {
			return $gateways;
		}

		$filtered = $gateways;
		// ... 按条件摘除

		// 资格、权限或地域限制过滤后为空时保持为空，交由界面解释不可用原因。
		return $filtered;
	}
}
```

支付资格、地域、权限及安全过滤必须失败关闭，筛空不能回退原列表。仅不涉及限制的纯展示排序/筛选可在明确产品设计下提供展示兜底，并解释空态；不得推广为通用规则。

只有一个钩子、没有共享状态的功能不要包类，`static function ()` 就地挂掉更短。

## 九、升级与迁移

```php
add_action(
	'plugins_loaded',
	static function (): void {
		$saved = (string) get_option( 'opc_xxx_version', '' );
		if ( OPC_XXX_VERSION === $saved ) {
			return;
		}

		// 需要迁移才在这里做，一次性的。
		update_option( 'opc_xxx_version', OPC_XXX_VERSION );
	}
);
```

不要每次请求都判断要不要迁移，那是白白的开销。

**不要用 `dbDelta` 自建业务表。** 自定义表带来三件事：备份要单独处理、卸载要不要删、以后改字段要写迁移。CPT + postmeta 能表达的东西就不要建表。真需要建表（比如大量订单行）时单独设计迁移、索引、权限、备份及卸载策略，并按当前项目变更流程确认范围。

## 十、卸载

`uninstall.php` 只在用户删除插件时执行。规则：

- 删自己建的 option（`opc_xxx_version` 之类）
- 删自己建的 transient
- **绝不** `DROP TABLE`
- **绝不**删客户的文章、页面、图片

## 十一、常见错误

| 现象 | 原因 |
| --- | --- |
| 后台报「无法修改响应头，已发送」 | 在 `template_redirect` 之后才 `header()`，改到 `send_headers` 里 |
| 后台或 admin-ajax 内存耗尽 | 在 `map_meta_cap` 里调了 `current_user_can()`，递归 |
| 区块编辑器作者选择报错 | REST 把 `/wp/v2/users` 对已登录也摘了 |
| 短代码内容跑到页面最上面 | 直接 `echo` 没有 `ob_start()`／`ob_get_clean()` |
| CPT 详情页 404 | 没刷新重写规则，或 `rewrite` slug 和已有页面冲突 |
| 设置保存后变空 | `register_setting` 没给 `sanitize_callback`，或字段名与 option 名不一致 |
| 表单提交后跳回原页但没提示 | 用了 `wp_redirect` 而不是 `wp_safe_redirect`，被安全策略拦下 |
| 装了两个插件都改同一处、互相覆盖 | 过滤器的优先级没写，默认 10 撞在一起 |
