# 国内版开发、部署与回滚

## 1. 本地开发

优先阅读 mcwlapi 的：

- `docs/2026-10-10-国内开发备忘.md`
- `docs/2026-10-10-数据库变更.md`
- `scripts/domestic-test.ps1`

历史国内开发文档约定 `dev` 分支，前端 3101、后端 3201、Delve 2301，数据库 `mcwlapi_domestic_dev`。执行前核对当前分支、脚本默认值和端口；不要擅自切分支或启动/停止已有服务。

在 `C:/code/mcwlapi` 中，按需且经授权执行：

```powershell
.\scripts\domestic-test.ps1 -Action Status
.\scripts\domestic-test.ps1 -Action Start
.\scripts\domestic-test.ps1 -Action Start -DebugBackend
.\scripts\domestic-test.ps1 -Action Restart
.\scripts\domestic-test.ps1 -Action Stop
```

Start/Restart/Stop 会改变本地进程状态；不要在纯排查请求中自动执行。确认数据库、Redis、Go/Bun 等实际依赖，不为本技能另造一套启动器。

## 2. 实例规划

以下是历史部署文档约定，不代表当前机器已运行：

| 端口 | 服务 |
|---|---|
| 12300 | mcwlapi / new-api |
| 12301 | CPA GPT |
| 12302 | CPA Gemini / Claude |
| 12303 | CPA Mixed |

新部署只需 GPT/Claude 时可精简为两个 CPA 实例，不必复制全部历史分组；端口、进程名、账号目录和服务 Key 必须一一对应。

参考来源：

- mcwlapi `docs/2026-09-12-国内部署指南.md`
- mcwlapi `docs/2026-09-12-CPA路由与定价.md`
- mcwlcpa `deploy/linux/QUICK_START.md`
- 两个仓库的 `deploy.ps1`、`upload.ps1`

文档可能内含历史示例凭据，不复制真实值。调用上传脚本前先读参数定义和目标清单，不使用文档中的域名作为默认生产目标。

## 3. 生产配置

mcwlapi 主要配置入口包括 `PORT`、`GIN_MODE`、`SQL_DSN`、`TENANT_ROOT_DOMAIN`、`PLATFORM_HOSTS`、`GENERATE_DEFAULT_TOKEN`、`SESSION_COOKIE_SECURE`。确认当前加载逻辑及 Cookie/TLS 配置，不能把历史开发 `SESSION_COOKIE_SECURE=false` 原样当作 HTTPS 生产基线。

数据库 DSN、会话密钥和上游 Key 仅存私有部署配置。设置足够随机的会话密钥，关闭不必要的默认令牌生成。不要直接执行可能重置已有数据的初始化脚本。

CPA 参考 account-pool 的版本差异。默认仅回环监听、管理 API 关闭或仅本机可访问。禁止在公网 Nginx 中无差别代理 CPA 管理接口。

## 4. Nginx 流式反代

下面是需要合并进现有站点的 location 片段，不是完整 TLS/安全配置：

```nginx
location / {
    proxy_pass http://127.0.0.1:12300;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Connection "";
    proxy_buffering off;
    proxy_cache off;
    proxy_request_buffering off;
    proxy_read_timeout 3600s;
    proxy_send_timeout 3600s;
    send_timeout 3600s;
    add_header X-Accel-Buffering no always;
}
```

保留 Host 以正确识别租户。转发头只信任实际代理，CPA 的 `server.trusted-proxies` 按拓扑设置；不要对任意来源无条件信任。WebSocket 另设 upgrade 规则，不能沿用 `Connection ""` 就宣称支持。

发布前测试 Nginx 配置，再重载；先确认影响范围。大文件上传限制按视频素材需求设置，不盲目取消大小限制。

## 5. 发布步骤

1. 确认环境、目标机器/目录、域名、分支、数据库与可停机窗口。
2. 记录当前提交、二进制、私有配置版本、进程管理方式；备份数据库和必要配置，备份不进入技能包。
3. 本地构建并做限定测试；先阅读脚本，确认它不会携带 auths 或开发配置上传。
4. 先部署 CPA 并本机验收，再配置/部署网关，最后验收公网 TLS/流式和租户路径。
5. 同一服务只用一个进程管理器。历史部署用宝塔 Go 项目，systemd unit 仅备用；不要两者同时启动。
6. 观察错误率、首 token 延迟、账号可用性和结算；通过后再扩大分组或流量。

## 6. 回滚

恢复上一版二进制与配套配置，使用原进程管理器重启并验收。涉及数据库变更时优先选择向后兼容的迁移；恢复数据库是独立高风险操作，先确认备份时点与增量写入影响。不要简单恢复旧库而丢失新发生的余额、订单或任务记录。

本技能只提供部署流程；创建时没有构建、上传、登录或修改两个业务项目。
