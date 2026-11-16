---
name: ops-linux
description: Ubuntu 22/24 主机运维知识手册：LNMP、WordPress、Hyperf、Go、Python 五类服务的systemd守护、Nginx反向代理、权限属主、日志磁盘、备份回滚与故障对照表；供运维专员在已授权服务器上排查故障与安全变更前查阅。
---

# Linux主机运维手册（Ubuntu 22/24）

> 先读取当前project brief、合同政策和验收清单，确定范围、费用、服务窗口与回滚要求；缺项询问，不内置价格或SLA。先只读识别操作系统、包管理器、服务管理器、部署路径和运行用户；以下Ubuntu/systemd示例仅在现场匹配时使用。
> 深度命令速查见 [references/commands.md](references/commands.md)。

## 常见技术栈（先按现场核实，不是默认库存）

| 层 | 用什么 | 部署形态 | 端口/入口 |
|---|---|---|---|
| 系统 | **Ubuntu Server 22.04 / 24.04 LTS** | apt + systemd | — |
| Web | **Nginx** | `nginx` 服务，vhost 在 `/etc/nginx/sites-available/` | 80 / 443 |
| PHP-FPM（LNMP） | PHP 7.4—8.5，Ubuntu 22 默认 8.1，24 默认 8.3 | `php-fpm<版本>` 服务，Unix socket | `/run/php/php8.3-fpm.sock` |
| **WordPress** | 核心、主题与插件版本现场清点 | Nginx → php-fpm（按实际配置） | 走实际Web端口 |
| **Hyperf** | PHP + Swoole 常驻内存 | **长驻进程，不是 php-fpm**；systemd/supervisor 守护 | 默认 9501，Nginx 反代 |
| **Go** | 编译成单个二进制 | systemd 守护，Nginx 反代 | 常用 8080 |
| **Python** | venv + gunicorn（WSGI）或 uvicorn（ASGI） | systemd 守护，Nginx 反代 | 常用 8000 |

**一句话分水岭**：WordPress / 普通 PHP 走 `fastcgi_pass` 到 php-fpm；**Hyperf、Go、Python 都是自己监听端口，Nginx 只做 `proxy_pass` 反代**。用错指令的典型表现是直接 502。

Ubuntu 之外的系统（CentOS 7 已 EOL、AlmaLinux 等）只在客户环境里被动遇到，遇到时先查 `/etc/os-release` 再决定命令，不套 Ubuntu 的经验。

## 开工前四问（缺一不动手）

1. **授权**：这台机器客户是否书面授权？账号或面板入口从哪来？
2. **归属**：域名、服务器、数据库分别在谁名下，是否客户本人账号。
3. **路径**：站点根目录、属于哪类服务（WP / Hyperf / Go / Python）、版本、数据库名。
4. **回滚**：改之前备份在哪、怎么还原。没有回滚路径就先建备份，或书面写「无回滚路径，风险由客户确认」。

答不上来先回主理人，不自己猜。

## systemd示例（仅适用于实际采用systemd的环境）

三类自研服务都写成 `/etc/systemd/system/<名字>.service`：

| 服务 | ExecStart 示例 | 关键配置 |
|---|---|---|
| Go 二进制 | `/opt/app/server --config /opt/app/config.yaml` | `Restart=always`、`WorkingDirectory`、非 root 用户 |
| Hyperf | `/usr/bin/php /opt/hyperf/bin/hyperf.php start` | `Restart=always`、不能用 `php-fpm` 思路重启 |
| Python | `/opt/app/venv/bin/gunicorn -w 4 -b 127.0.0.1:8000 app:app` | venv 绝对路径、WorkingDirectory |

改完服务文件必须 `systemctl daemon-reload`，然后 `restart` + `status` + 实际请求验证，三件事缺一不可。

**Hyperf 特别注意**：代码是常驻内存的，**改了 PHP 代码必须重启进程才生效**（`php bin/hyperf.php start` 起的进程不会热更新）。改配置同理。线上用 `supervisor` 或 systemd 保证挂了自动拉起。

## Nginx 两种接法（别混）

```nginx
# WordPress / 普通 PHP → fastcgi
location ~ \.php$ {
    include snippets/fastcgi-php.conf;
    fastcgi_pass unix:/run/php/php8.3-fpm.sock;
}

# Hyperf / Go / Python → 反代
location / {
    proxy_pass http://127.0.0.1:9501;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

改完 `nginx -t` 再 `systemctl reload nginx`。`nginx -t` 不过就别 reload。

## 权限与属主（站点问题一半出在这）

- **Web 服务用户别猜**：同时核对站点目录、Web/FPM进程、服务配置和ACL；部署用户不一定等于运行用户。
  确认方法：`stat`查看目标目录属主与权限，查询实际服务配置及进程用户；`www`和`www-data`都只是可能值。
- 目录755、文件644仅是普通公开文件示例，秘密配置和可执行文件按实际权限模型处理；仅给必要运行目录写权限，不使用777。
- 若确需更改属主，先列出精确对象和现场核实的用户/组，备份权限、用户批准后执行；不默认递归修改整站。
- PHP 开了 `open_basedir` 或宝塔「防跨站攻击」后跨目录读写会被拦，典型报错 **No input file specified**。
- Windows 传上来的文件带 CRLF 或 BOM，表现为页面顶部空行、session 报错、脚本 `#!/usr/bin/env` 找不到解释器。

## 一次看清机器（只读，先跑这套）

```bash
cat /etc/os-release && uptime && free -h
df -h && df -i
ss -lntup
systemctl --failed
```

宝塔机器：站点 `/www/wwwroot/<域名>/`，日志 `/www/wwwlogs/`，服务 `/www/server/`，备份 `/www/backup/`。非宝塔：站点常在 `/var/www/<域名>/`。

## 磁盘与日志

```bash
du -h --max-depth=1 /var/www 2>/dev/null | sort -hr | head -20
du -sh /var/log/* | sort -hr | head
find /var/www -mtime -1 -type f | head -50    # 近一天被改的文件，排查挂马常用
```

- 清大日志用 `truncate -s 0 <file>`，**不要 `rm` 正在被写入的日志**（进程持有句柄，空间不释放）。
- 系统日志：`journalctl --vacuum-size=200M`。
- 长期方案是 logrotate，别靠手工删。

## 计划任务

```bash
crontab -l -u root
crontab -l > /root/cron.bak.$(date +%F)   # 改之前先导出
```

- WordPress 站点建议 `define('DISABLE_WP_CRON', true)` + 系统 cron 每 5 分钟调 `wp-cron.php`，比默认靠访问触发稳。
- 定时命令末尾加 `>/dev/null 2>&1`，否则输出会堆邮件或撑爆磁盘。

## 故障对照表（现象 → 先查哪）

| 现象 | 优先排查 |
|---|---|
| **WP 白屏** | `wp-content/debug.log` → PHP 错误日志 → 插件/主题冲突（改名禁用验证）→ 内存耗尽 → opcache 缓存 → 属主 |
| **WP 内页 404** | 固定链接伪静态是否配置 → `nginx -t` → 站点根目录绑错 |
| **WP 后台慢 / 卡** | 慢插件 → `wp-cron` 堆积 → MySQL 慢查询 → 对象缓存缺失 |
| **Hyperf 访问 502** | 进程是否存活 → 端口 9501 是否在监听（`ss -lntup`）→ Nginx 是否误用了 fastcgi → 改代码后是否重启 |
| **Hyperf 改了不生效** | 常驻内存，必须重启进程；`.env` 是否被缓存（`runtime/container` 目录） |
| **Go 服务 502** | 二进制是否在跑 → 端口是否变过 → systemd `Restart` 是否在反复重启（`journalctl -u`）→ 二进制权限与配置文件路径 |
| **Python 服务 502** | venv 路径是否对 → gunicorn/uvicorn 是否监听 127.0.0.1 → 依赖是否装全 → 工作目录 |
| 504 | 上游处理超时 → `proxy_read_timeout` / `fastcgi_read_timeout` → 数据库慢查询 |
| 403 | 目录权限 → 缺 index → deny 规则 |
| 数据库连接失败 | mysqld 是否存活 → 账号密码 → socket 还是 127.0.0.1 → 磁盘是否满 |
| 站点突然很慢 | `top` → MySQL 慢查询 → 磁盘 IO → 带宽跑满 → 是否被采集或 CC |
| 证书告警 | 系统时间 → 证书链是否完整 → 域名是否匹配 |
| Too many open files | `ulimit -n` → systemd 的 `LimitNOFILE`（Hyperf/Go 高并发常见） |
| 上传失败 | `upload_max_filesize` / `post_max_size` / Nginx `client_max_body_size` 三处 |

每查一项记一次结论，不查完不写「已修复」。

## 备份与回滚

```bash
tar -czf /root/backup/site-<域名>-$(date +%F).tar.gz -C /var/www <域名>
mysqldump -u<用户> -p --single-transaction --default-character-set=utf8mb4 <库名> > db-<库名>-$(date +%F).sql
```

- Go / Python 服务除了代码还要备份**配置文件与 `.env`**；Hyperf 备份代码 + `.env`，`runtime/` 不用备份。
- **没验证过的备份只能写「未验证」**，不能写成「已备份」。验证：tar 能列出内容、SQL 能导入临时库、二进制能 `--version`。
- 回滚前先把当前状态也备份一份，否则回滚失败两边都没了。

## 高危命令清单（执行前必须书面确认）

`rm -rf` / `chmod -R 777` / `chown -R` / `reboot` / `kill -9` / `dd` / `mkfs` / `iptables -F` / 重装系统 / 直接改生产数据库 / `DROP DATABASE` / 覆盖式导入 / 在生产库跑 `wp db reset`。

这些是不可逆地改变客户资产，客户口头同意也要在订单记录里留一句，并回到主理人。

## 每次变更都要留下

改动清单（命令 + 作用范围）、备份位置、验证结果、回滚方式、残留风险、需用户确认项。写完通过 SendMessage 回传主理人。

## 边界

- 只做授权范围内的站点运维；**不做等保测评、不出渗透测试报告、不承诺安全结论**。
- 不做架构改造、不做集群、不承诺「性能提升 X%」。
- 涉及被黑、入侵、数据丢失或监管文书，先保护现场与备份，回主理人，按 `site-incident` 规程走。
- 不保存不外传客户密码与密钥；临时权限用完撤销并提醒客户改密码。
