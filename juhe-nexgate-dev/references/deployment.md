# 本地运行与发布

## 本地启动

先查端口、进程路径、目标数据库和项目脚本。主程序从工作目录加载 .env，godotenv.Load 不覆盖已有进程环境变量；不打印完整配置。进程环境覆盖适合临时测试，无需修改真实 .env。

- `scripts/domestic-test.ps1` 使用国内测试库、前端 3101、后端 3201、调试端口 2301，但会清空 REDIS_CONN_STRING，不能原样测试异步图片。
- `restart.ps1` 会停止 pid 文件和目标端口对应进程，参数 Port 不一定传入子进程。先读当前版本，确认进程归属，避免停止不相关进程。
- 项目 .env 可能使用本机 MySQL；不要因为默认 SQLite 就假设启动不会连接已有数据。数据库按用户任务选择并记录。
- Windows 后台进程使用隐藏窗口，或使用可停止的终端会话。不要在启动失败后留下多套服务抢端口。

异步图片本地环境示例（端口先确认空闲）：

```powershell
$env:PORT = '13000'
$env:REDIS_CONN_STRING = 'redis://127.0.0.1:6380/0'
$env:ASYNC_IMAGE_TASKS_ENABLED = 'true'
$env:ASYNC_IMAGE_WORKERS = '1'
$env:ASYNC_IMAGE_TIMEOUT_SECONDS = '600'
$env:ASYNC_IMAGE_QUEUE_KEY = 'new-api:async-images:local-test'
$env:GOOS = 'windows'
$env:GOARCH = 'amd64'
$env:CGO_ENABLED = '0'
go build -o .cache/local-api.exe .
if ($LASTEXITCODE -ne 0) { throw '本地构建失败，不运行旧二进制' }
& .\.cache\local-api.exe
```

这只是当前进程配置，数据库仍来自已有环境/工作目录 .env。开发构建可复用现有前端 dist，交付包必须重建前端。

Redis 要求 5.0+ 且允许 ZPOPMIN。2026-11-03 Windows 127.0.0.1:6379 实测为 3.0.504，现有限流、批量 HSET 也不兼容；WSL Redis 7 的独立 6380 测试通过。运行时重新核实 PING/INFO/命令能力，不能只检查端口。localhost 的 IPv4/IPv6 可能指向不同服务，排错时明确 IP。保留用户已有 Redis，不用 FLUSHALL/FLUSHDB 清理共享服务。

## 国内 / 国际打包

在各自工作树运行，核对当前 AGENTS 与脚本：

```powershell
.\package-linux.ps1 -Arch amd64 -BuildFrontend
```

- Go 内嵌 web/default/dist。正式发布先构建匹配前端，不把国内 dist 拷给国际版。
- 标准输出：releases/<yyyyMMdd>/new-api-linux-amd64.zip；根目录散落二进制不是标准交付包。
- 包含二进制及运行模板，保留仓库维护的初始化 SQL；不得包含真实 .env、数据库文件、业务数据导出或凭据。
- 解压后用 `go version -m <binary>` 确认 GOOS=linux、GOARCH=amd64、CGO_ENABLED=0。
- deploy.ps1 使用打包流程且可能导出 SQL；仅打包优先 package-linux.ps1。upload.ps1 部署已构建包，mcwlcpa 的部署是另一项操作。
- 检查归档内容、版本、大小与 SHA256；发布说明沿用目标 releases 风格，不编造验证平台。

## 远端部署与反代

仅在用户要求时上传、SSH、重启或 push。主机、进程管理器、端口、库和域名来自当前配置，不从旧文档猜测；不默认增加备份、TLS、另一进程管理器或高可用改造。

历史国内拓扑为网关 12300、CPA GPT 12301、Gemini/Claude 12302、Mixed 12303，仅作参考。公网客户默认地址与内部国内部署地址分开维护。

反代保留 Host，正确设置受信任代理；SSE 关闭响应缓冲，超时按需求设置；WebSocket 单独设置 Upgrade。CPA 管理 API 不通过通用公网 location 暴露。上线验证 status、鉴权、目标协议、任务和账务，记录版本；不通过恢复旧数据库覆盖新发生的消费/订单。
