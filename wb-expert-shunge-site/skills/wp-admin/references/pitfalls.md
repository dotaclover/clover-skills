# 后台实操的坑（全部来自线上实测）

> 每一条都写成「症状 → 原因 → 怎么办」。带 ★ 的是会让人误判成「功能坏了」的。
> 出现新的坑，直接往这份文件里加，不要只记在脑子里。

## 一、界面与入口

**★1. 客户点「外观 → 设计」进了站点编辑器，改两下前台就变形了**
原因：WordPress 7.x 对经典主题也挂出「设计」「字体」。那里改的是模板，改坏不报错。
处理：`site-site-kit/includes/admin-ui.php` 已移除菜单并拦截直连地址（`site-editor.php`、`font-library.php` 挡回 `themes.php`）。改这四条要跑 `test_admin_ui.php`。

**★2. 自定义器里的「颜色」段改了没反应**
原因：那是 WordPress 自带的全局色板，主题配色走「配色方案」。两个都留着，客户会以为没保存成功。
处理：`customize_register` 优先级 20 时 `remove_section('colors')`。

**3. 页面列表里多出一页英文 `Privacy Policy` 草稿**
原因：安装器可能创建默认隐私草稿，也可能是用户正在编辑的内容。
处理：先只读核对对象ID、创建来源、内容及隐私页引用；不得按英文标题或draft状态批删。仅本任务创建且用户确认可移除的对象优先移入回收站，永久删除另行授权。

**★4. 复选框看着是全开的**
原因：读 `input.value` 恒为 `1`，跟 `checked` 无关。曾经据此误判「演示站允许注册」，其实早就关了。
处理：读 `checked`；命令行 `wp option get users_can_register`。

## 二、块编辑器（页面 / 产品）

**5. 第一次进编辑器，什么都点不动**
原因：弹「欢迎指南」模态，`body` 带 `modal-open`。
处理：找 `.components-modal__frame` 里 aria-label 含「关闭/Close」的按钮点掉，再等 `wp.data` 就绪。

**★6. 点「保存」后界面显示已更新，前台却没变**
原因：点完按钮立刻跳走，会打断还没发出去的保存请求。
处理：等 `wp.data.select('core/editor')` 的 `isSavingPost()` 为 false 且 `isEditedPostDirty()` 为 false；读前台时加随机参数绕缓存。

**★7. 新文章点「发布」没反应**
原因：新文章第一次点只是展开确认面板（`.editor-post-publish-panel`），真正提交要点面板里的按钮；而它的 toggle 类名是 `editor-post-publish-button__button`，不是 `editor-post-publish-button`。另外 React 按钮用 `element.click()` 有时不触发。
处理：先找 `.editor-post-publish-panel__header-publish-button button`，没有就真实点击 `.editor-post-publish-panel__toggle`，再点面板按钮。

**8. 保存后离开页面，导航卡死一分钟**
原因：有未保存改动时 Chrome 弹 `beforeunload` 确认框，自动化不点掉就永远等。
处理：先检查保存状态及当前操作；只对预期类型和已授权动作处理dialog，不注册无差别`accept()`。未保存离开提示默认取消并等待保存；删除/权限等确认须核对对象与授权，未知弹窗停止。

**9. 段落一个都找不到**
原因：我们的页面把内容包在 `core/group` 里，只查顶层区块拿不到段落。
处理：递归 `innerBlocks` 再找 `core/paragraph`。

**10. 表单刚提交完就跳转，报 `net::ERR_ABORTED`**
原因：上一个请求还没收尾。不是页面坏了。
处理：先按本次唯一测试标记/对象ID查后台记录和请求状态；结果未知时停止，不直接重提。确认原请求未成功且获得重试授权后才重试，防止重复预约、邮件或业务记录；页面读取等待目标元素就绪。

## 三、自定义器（配色）

**★11. 点完「发布」立刻读前台，颜色没变**
三个原因叠在一起：
- `wp.customize.state('saved')()` **在点下去那一刻就已经是 true**，等它等于没等；
- `state` 里**没有 `dirty` 这一项**（只有 saved/saving/trashing/activated…），写 `state('dirty')()` 会直接报「不是函数」；
- 前台 HTML 有页面缓存，浏览器读到旧页面。
处理：等 `state('saving')()` 为 false 且 `Object.keys(dirtyValues()).length === 0`；读前台用 `/?site_walk=<时间戳>` 并关掉浏览器缓存（`setCacheEnabled(false)`）。

**★12. 色块点了没选中**
原因：点击监听挂在 `api.bind('ready')` 里，点早了没反应、也不报错。
处理：点完校验 `wp.customize('site_site_kit[theme]').get()`，没变就再点，最多三次，再发布。

**★13. 验收读 `document.documentElement` 拿到的是默认色**
原因：配色变量声明在 `body` 的 `.site-style-*` 上，不在 `:root`。
处理：读 `getComputedStyle(document.body).getPropertyValue('--site-brand')`。

## 四、前台缓存

**★14. 客户改完刷新看不到变化，反复保存**
原因：`site-slim` 原来给匿名页发 `Cache-Control: public, max-age=300`，浏览器 5 分钟内不回源。
处理：2026-11-01 起改成 `max-age=0, s-maxage=600`——浏览器每次回源确认，CDN 仍可缓存 10 分钟。验：`curl -skI https://<站>/ | grep -i cache-control`。

## 五、用户与登录

**★15. 新建用户报「密码不匹配」**
原因：两个密码框。WP 的密码强度脚本会重置第二个框，两个都手动填反而对不上；提示也不说是哪个字段出了问题。
处理：只填 `#pass1` 并派发 `input` 事件，`#pass2` 交给页面脚本。

**16. 提交建用户按钮没反应**
处理：真实点击 → 键盘回车 → JS 点击，三种依次试（页面自己的脚本会同步密码框，绕过去直接 POST 会报「密码不匹配」）。

**17. 删除用户确认页点错按钮**
原因：页面上有一个「应用」筛选按钮（`#screen-options-apply`）也是 submit，按 `input[type=submit]` 取第一个会点错。
处理：按 `#submit` 取；等它出现再点。

**18. 登录偶发被 `reauth=1` 打回**
原因：登录页 JS 与 test cookie 没就绪就提交；后台仪表盘有心跳轮询，`networkidle2` 与 `waitForNavigation` 都可能等不到。
处理：轮询 `page.url()` 判断是否离开登录页，失败重来一次，再退到直接打开 `/wp-admin/`。

**19. 连续跑脚本被 429「尝试次数过多」**
原因：`site-harden` 限速——同 IP 5 分钟内超过 10 次登录直接挡回。这是设计如此，别关。
处理：脚本跑批时串行、别并发；撞上了等 5 分钟。正常登录成功会清零计数。

## 六、表单与演示环境

**20. 演示站预约/询盘永远是「邮件发送失败」**
原因：可能未配置SMTP，也可能认证、网络或投递失败。
处理：核对实际配置、发送日志与收件结果，不因“演示站”名称忽略失败；交付按本项目通知验收要求记录，后台记录不等于邮件送达。

**21. 用 REST `search` 验中文标题偶发查不到**
处理：改用客户真正看到的页面验收（产品归档 `/products/`、业务页），别依赖搜索接口。
