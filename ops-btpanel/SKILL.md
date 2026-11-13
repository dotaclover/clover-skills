---
name: ops-btpanel
description: 宝塔面板运维知识手册：面板入口与加固、bt命令、LNMP建站、PHP版本与扩展、MySQL、SSL申请续期、反向代理跑Hyperf/Go/Python、计划任务、备份与常见报错速查；供运维专员在已授权面板内操作前后查阅。
---

# 宝塔面板运维手册

> 仅在现场确认使用宝塔时应用本手册；先核实版本、路径与权限。范围、费用、服务窗口从当前project brief、合同政策及验收清单取得，缺项询问，不内置价格。新建站点、登记、证书部署优先当前支持的界面/API，不直接写内部数据库；写入、重启、删除先确认并备份回滚。
> 站点迁移步骤见 [references/migration.md](references/migration.md)。**把本地产物更新到已存在站点**（备份、上传、覆盖、属主、验证、回滚）走 `ops-deploy`。

## 面板入口与安全加固（接手新机器先做这几件）

1. **看入口**：由用户提供受限面板入口，确认目标与授权；不要把会输出密码的默认信息命令当常规探测，凭据仅由用户在安全界面查看。
2. **改端口**：默认 8888 太招扫描，面板设置里改掉，并在**腾讯云防火墙/安全组放行新端口、限制来源 IP**。
3. **开面板 SSL + 绑定域名**，不要长期用 `http://IP:8888` 登录。
4. **改密码、开二次验证（Google Authenticator）**。
5. 面板日志：`/tmp/panelExec.log`；面板打不开时先看它。

**不要做的**：把 8888 对 0.0.0.0/0 长期开放；把面板账号密码贴进聊天记录或仓库。

## 常用 bt 命令

面板命令和菜单编号以当前版本帮助为准。状态/日志先只读，日志须脱敏；start/stop/restart与凭据重置属于变更，用户确认后执行。不在自动化日志中输出默认账号密码。

## 目录结构

| 路径 | 用途 |
|---|---|
| `/www/wwwroot/<域名>/` | 站点根目录 |
| `/www/wwwlogs/` | 站点访问与错误日志 |
| `/www/server/` | 服务安装目录（nginx、php、mysql） |
| `/www/server/panel/` | 面板自身 |
| `/www/backup/` | 备份目录（站点/数据库） |
| `/www/server/cron/` | 计划任务脚本 |

## 建站（LNMP）

添加站点 → 填域名（可一次填多个，每行一个）→ 根目录默认 `/www/wwwroot/<域名>` → 选 PHP 版本 → 需要就同时建数据库 → **FTP 默认不用建**（多一个入口多一份风险）。

- 站点建完先访问一次确认默认页能开，再传程序。
- 默认首页顺序在站点「默认文档」里调，静态站要把 `index.html` 放前面，WP 是 `index.php`。
- **伪静态**：WordPress 选 `wordpress` 模板（等价于 `try_files $uri $uri/ /index.php?$args;`）；ThinkPHP、Laravel 有对应模板；自研 PHP 用 `rewrite` 或手写。

## PHP 管理

- **多版本共存**：面板可同时装 7.4 / 8.0 / 8.1 / 8.2 / 8.3，每个站点单独选。Ubuntu 22 建议 8.1，24 建议 8.3。
- **常用扩展**：`fileinfo`、`opcache`、`redis`、`imagick`、`zip`、`bcmath`、`exif`、`gmp`。WP 缺 `imagick` 会无法处理图片，缺 `zip` 无法在线升级。
- **参数**（php.ini）：`upload_max_filesize`、`post_max_size`、`memory_limit`、`max_execution_time`。改完要重启对应 PHP 服务。
- **禁用函数**：`putenv`、`proc_open`、`pcntl_*` 被禁用会导致 Composer 无法执行、Hyperf 无法启动。**跑 Hyperf 必须放开 `putenv`、`proc_open`、`pcntl_*` 等 Swoole 需要的函数**，并确认 Swoole 扩展已装。
- **opcache**：改了 PHP 文件不生效时，先重启 PHP 或清 opcache，别急着改代码。

## MySQL

- 建库建用户：面板「数据库」页，字符集选 `utf8mb4`。
- 导入导出：小库用面板，大库用命令行（`mysql` / `mysqldump`），面板有大小与超时限制。
- 面板的 phpMyAdmin 用完就关掉或改路径，不要长期暴露。
- 数据库突然连不上：先看 mysqld 是否在跑、磁盘是否满、是否 OOM 被杀。

## SSL

- 面板「SSL」页可申请 Let's Encrypt，**前提：域名解析已生效 + 80 端口可访问**。
- 申请失败的常见原因：解析没生效、80 被防火墙拦、面板证书验证路径被伪静态规则拦截、域名指向的不是这台机器。
- Let's Encrypt 有效期 90 天，面板会建自动续期任务，**要检查一次是否真的续成功**，别默认。
- 开「强制 HTTPS」前确认所有资源都是 HTTPS，否则 mixed content 导致图片/样式加载不出来。
- 证书链不完整会导致部分安卓或微信内打不开，用面板给的完整链。

## 在宝塔上跑 Hyperf / Go / Python（反向代理，不是 PHP 站点）

这三类都是自己监听端口的常驻服务，**不要建成 PHP 站点**：

1. 站点 → **反向代理** → 添加：代理名称自定义，目标 URL 填 `http://127.0.0.1:<端口>`（Hyperf 9501 / Go 8080 / Python 8000）。
2. 服务本身用 systemd 或 supervisor 守护（写法见 `ops-linux` 手册）。
3. 端口**不要对外开放**，只在服务器内部让 Nginx 转发。
4. 502 时按顺序查：进程在不在 → 端口在不在监听（`ss -lntup | grep <端口>`）→ 反代目标地址是否填错 → 改代码后是否重启。

宝塔也提供「Supervisor 管理器」和「进程守护管理器」，可以用它们托管 Hyperf/Go/Python 进程，但同样要写清工作目录与启动命令。

## WordPress 在宝塔上

- 上传后只读核对站点属主、Web/FPM运行用户及ACL，`www`或`www-data`均不可预设。权限修复限本次获批对象，先备份权限，不递归重设整站。
- 开启「防跨站攻击（open_basedir）」后跨目录访问被拦，表现为 **No input file specified** 或插件读写失败。
- 伪静态必须选 `wordpress`，否则内页全 404。
- 白屏排查：面板看 PHP 错误日志 → 逐个停用插件 → 切默认主题。
- 我们交付的是瘦身定制版 + `opc-slim` 等自家插件（兼容 PHP 7.4–8.5、WordPress 6.5+），升级 WP 核心前先确认插件兼容。

## 计划任务

面板「计划任务」可加：备份站点、备份数据库、释放内存、切割日志、访问 URL（用来触发 WP cron）。

- **WordPress 建议**：`wp-config.php` 里 `define('DISABLE_WP_CRON', true)`，再加一条每 5 分钟访问 `wp-cron.php` 的计划任务，比靠访问触发稳。
- 备份任务要指定保留份数与存储位置（本地/COS/FTP），并定期验证备份能恢复。

## 备份

- 「备份」页或计划任务：站点备份（文件）、数据库备份（SQL）。
- 本地备份不算备份——机器没了就没了。重要站点配远程存储（COS 或客户自己的网盘）。
- **没验证过的备份写「未验证」**，不写「已备份」。

## 常见报错速查

| 报错 | 先看 |
|---|---|
| No input file specified | open_basedir/防跨站、PHP 版本选错、根目录绑错、文件属主 |
| 502 Bad Gateway | PHP-FPM 是否存活、进程数耗尽、sock 路径；反代场景看目标端口 |
| 404（内页） | 伪静态没配、根目录错、Nginx 配置未生效 |
| 403 | 目录权限、缺 index、deny 规则 |
| 500 | PHP 致命错误，看站点错误日志与 `debug.log` |
| 面板打不开 | 服务是否挂、端口是否放行、磁盘是否满、看 `/tmp/panelExec.log` |
| 软件装不上/卡住 | 磁盘空间、内存不足、apt 源慢（可换源）、网络 |
| 上传失败 | `upload_max_filesize`、`post_max_size`、Nginx `client_max_body_size` |
| 邮件发不出 | 云厂商封 25 端口，用 SMTP 插件走 465/587 |
| 改了 PHP 代码没变化 | opcache 缓存、改错站点目录、常驻服务未重启 |

## 高危操作（执行前书面确认）

卸载面板、重装系统、修复面板（会重置权限）、批量删除站点/数据库、改 MySQL root 密码、升级 PHP 主版本、清理 `/www/backup` 里的历史备份。

## 边界

- 只操作已授权的面板；面板账号密码不进仓库、不进聊天记录。
- 面板提供的「一键迁移」「一键部署」类功能，执行前先确认它会改什么。
- 面板告警类信息（被入侵提示、异常登录）如实转给主理人，不自行判断「没事」。
