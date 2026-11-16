# Linux命令速查（示例需先核对发行版与服务管理器）

按场景分节，需要哪节读哪节。删除、覆盖、重启类命令执行前必须书面确认。

## 1. 系统与资源

```bash
cat /etc/os-release
uname -r && uptime && nproc && free -h
df -hT && df -i
lsblk && hostname -I
top                                  # 交互看负载，q 退出
vmstat 1 5                           # CPU/IO/上下文切换
iostat -x 1 5                        # 磁盘 IO（需 apt install sysstat）
```

## 2. systemd（所有自研服务都用它）

```bash
systemctl status <服务> --no-pager
systemctl restart <服务> && systemctl status <服务> --no-pager
systemctl enable --now <服务>        # 开机自启并立即启动
systemctl daemon-reload              # 改了 .service 文件后必须执行
systemctl --failed
systemctl list-units --type=service --state=running | grep -E 'nginx|php|mysql|redis'
journalctl -u <服务> -n 200 --no-pager
journalctl -u <服务> -f              # 实时跟
journalctl -u <服务> --since "2 hours ago" --no-pager
```

服务文件位置：`/etc/systemd/system/<名字>.service`。最小可用模板（以 Go 为例）：

```ini
[Unit]
Description=app service
After=network.target

[Service]
Type=simple
User=<现场确认的专用运行用户>
WorkingDirectory=/opt/app
ExecStart=/opt/app/server --config /opt/app/config.yaml
Restart=always
RestartSec=3
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
```

## 3. Nginx

```bash
nginx -t                             # 改完必测，不通过不 reload
systemctl reload nginx
ls /etc/nginx/sites-available/ && ls -l /etc/nginx/sites-enabled/
tail -n 100 /var/log/nginx/error.log
tail -n 100 /var/log/nginx/access.log
```

WordPress / 普通 PHP 用 `fastcgi_pass unix:/run/php/php8.3-fpm.sock`；Hyperf / Go / Python 用 `proxy_pass http://127.0.0.1:<端口>`。

## 4. PHP-FPM（LNMP）

```bash
php -v && php -m                     # 版本与已装扩展
ls /run/php/                         # 真实 sock 路径，vhost 里要一致
systemctl restart php8.3-fpm         # Ubuntu 24；22 是 php8.1-fpm
tail -n 100 /var/log/php8.3-fpm.log
php -i | grep -E 'memory_limit|upload_max_filesize|post_max_size|max_execution_time'
```

宝塔机器路径是 `/www/server/php/<版本>/`，sock 在 `/tmp/php-cgi-<版本>.sock`。

## 5. MySQL / MariaDB

```bash
systemctl status mysql
mysql -e "SELECT VERSION();" && mysql -e "SHOW DATABASES;"
mysql -e "SHOW PROCESSLIST;"         # 看卡住的查询
mysql -e "SHOW VARIABLES LIKE 'max_connections';"
mysqldump -u<用户> -p --single-transaction --default-character-set=utf8mb4 <库名> > db.sql
mysql -u<用户> -p <库名> < db.sql    # 导入（覆盖式，高危）
tail -n 100 /var/log/mysql/error.log
```

导入前备份当前库并批准数据覆盖范围；长任务使用受管理任务或已批准的服务调度，保留日志与退出状态，不使用脱离管理的后台命令。

## 6. WordPress

```bash
cd /var/www/<域名>
wp --info                            # WP-CLI 是否可用
wp core version && wp plugin list && wp theme list
wp plugin deactivate <插件>          # 白屏排查先逐个停用插件
wp option get siteurl && wp option get home
wp db export backup.sql              # 或 mysqldump
wp cache flush
wp cron event list                   # 定时任务堆积排查
find . -type f -newermt '-2 days' | head -30   # 找最近被改的文件（挂马排查）
```

- 调试：临时在 `wp-config.php` 开 `WP_DEBUG` + `WP_DEBUG_LOG`，看 `wp-content/debug.log`，**查完关掉**。
- 固定链接 404：Nginx 要 `try_files $uri $uri/ /index.php?$args;`。
- 站点搬家后首页正常内页 404，多半是 `.htaccess` 没转成 Nginx 规则或 `siteurl/home` 没改。

## 7. Hyperf（Swoole 常驻）

```bash
cd /opt/hyperf
php bin/hyperf.php start             # 前台启动；生产用 systemd/supervisor
php bin/hyperf.php stop              # 或 systemctl stop
ps aux | grep hyperf                 # 看进程与 worker 数
ss -lntup | grep 9501
tail -f runtime/logs/hyperf.log
```

- **改代码必须重启**：常驻内存不热更新。
- 改 `.env` 后如不生效，清 `runtime/container/` 缓存再重启。
- Swoole 编译版本要和 PHP 版本匹配；PHP 升级后 Swoole 必须重新装/重装扩展。
- 不要把它当成普通 PHP 站点配 `fastcgi_pass`，那是 502 的头号原因。

## 8. Go

```bash
cd /opt/src/app
GOOS=linux GOARCH=amd64 go build -o /opt/app/server .
systemctl restart app && journalctl -u app -n 50 --no-pager
/opt/app/server --version            # 验证二进制可用
ss -lntup | grep 8080
```

- 交叉编译在本地做，服务器只放二进制 + 配置文件，不装 Go 环境。
- 静态二进制若用 cgo 会依赖 glibc，Alpine 上跑不起来；Ubuntu 一般没问题。
- 二进制权限 `chmod +x`，配置与 `.env` 属主给运行用户。

## 9. Python

```bash
cd /opt/app
source venv/bin/activate
pip install -r requirements.txt
python -c "import sys; print(sys.executable)"   # 确认用的是 venv
systemctl restart app
/opt/app/venv/bin/gunicorn -w 4 -b 127.0.0.1:8000 app:app   # 手动验证能否起
```

- systemd 里一律写 venv 的绝对路径（`/opt/app/venv/bin/gunicorn`），不能写 `source venv/bin/activate`。
- 依赖装不上先看 Python 版本是否对（`python3 --version`），Ubuntu 24 默认是 3.12。
- 服务起不来先看 `journalctl -u`，多半是模块找不到或端口被占。

## 10. 端口与连接

```bash
ss -lntup
ss -lntup | grep -E ':80|:443|:8080|:8000|:9501'
lsof -i:9501
ss -ant | awk '{print $1}' | sort | uniq -c
awk '{print $1}' /var/log/nginx/access.log | sort | uniq -c | sort -nr | head -20   # TOP IP
```

## 11. 权限与属主

```bash
stat -c '%U:%G %a %n' "$SITE_DIR"
ps -eo user,group,args
```

先从用户确认配置解析`SITE_DIR`，再核对Web/FPM进程与配置、部署用户及ACL。仅对获批的精确对象调整属主/权限，先保留原权限及回滚方案，不默认`www`、`www-data`或递归chmod/chown。

需要写入的目录（uploads / runtime / logs）单独放宽，不要整站 777。

## 12. 备份

```bash
tar -czf /root/backup/site-<域名>-$(date +%F).tar.gz -C /var/www <域名>
tar -tzf /root/backup/site-<域名>-2026-10-26.tar.gz | head   # 验证可读
ls -lh /root/backup/
```

备份要包含：站点文件、数据库导出、配置文件/`.env`、**systemd 服务文件内容**。恢复演练至少验证前两项。
