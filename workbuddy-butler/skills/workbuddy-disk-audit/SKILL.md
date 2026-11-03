---
name: workbuddy-disk-audit
description: Audit and reclaim local disk space used by WorkBuddy. Use when the user reports WorkBuddy taking too much space, asks to clean caches or deleted-session residue, wants to prune workspaces, or says deleting chats freed nothing. Covers inventory, safe permanent deletion (bypassing the recycle-bin redirect), Windows recycle-bin forensics, and session/workspace record cleanup.
---

# WorkBuddy 空间审计与回收

把 WorkBuddy 在本机占的每一块地方盘清楚，按"能不能安全删"分类，备份后回收。

## 目录地图

| 位置 | 说明 |
|---|---|
| `%WORKBUDDY_CONFIG_DIR%`（默认 `~/.workbuddy`） | 主数据目录：数据库、会话、插件、运行时 |
| `%APPDATA%\WorkBuddy` | Electron 主进程数据：`CachedData`、`WebStorage`、`CrashReport`、各分区 |
| `%LOCALAPPDATA%\Programs\WorkBuddy` | 当前安装，**不要手删** |
| `%USERPROFILE%\WorkBuddy` | 旧版本安装残留 + 历史临时工作空间，需逐层判断 |
| `C:\$Recycle.Bin\<SID>` | 删除项实际停留处，同占磁盘 |

`.workbuddy` 内部大头：

| 子目录 | 真实内容 |
|---|---|
| `binaries/` | Node / Python / PortableGit，删了技能全废 |
| `blobs/` | 内容寻址的聊天附件与图片 |
| `plugins/` | 插件本体（`marketplaces/`）+ 缓存（`cache/`） |
| `projects/<转义路径>/<uuid>.jsonl` | 会话正文 |
| `workspace/sessions/<uuid>/modify_backup/` | **回滚备份，不是聊天记录**，占会话数据的九成 |
| `changes-detail/`、`changes-index/`、`file-tree-manifests/` | 改动 diff 详情、索引、文件树快照 |
| `app/session/` | Chromium 分区缓存，登录态在 `Partitions/*/Cookies` |
| `logs/` | 日切日志，当天文件被进程占用 |

## 脚本

全部在 `scripts/`，Windows + Python 3，无第三方依赖。

### 1. 出台账

```bash
python scripts/scan_space.py          # 人读
python scripts/scan_space.py --json   # 机器读
```

输出四个位置的总量、`.workbuddy` 一级目录（带 A/B/C/D 档位）、按工作空间归组的会话数据、回收站里 WorkBuddy 相关条目、磁盘可用。

### 2. 永久删除（关键）

```bash
python scripts/purge.py --dry-run <路径>
python scripts/purge.py <路径> [<路径>...]
python scripts/purge.py --list paths.txt
```

本机 Python 的删除可能被 safe-delete 垫片重定向到回收站，`shutil.rmtree` 后目录"消失"但空间不变。本脚本走 `SHFileOperationW` 且不带 `FOF_ALLOWUNDO`，是真删。默认拒绝删盘根、`workbuddy.db`、`binaries`、`blobs`，确需加 `--force`。

### 3. 回收站取证

```bash
python scripts/recycle_audit.py                     # 总览 + WorkBuddy 相关
python scripts/recycle_audit.py --match .cleanup --top 30
python scripts/recycle_audit.py --purge --match .cleanup
```

解析 `$I*` 元数据还原原始路径，能精确到"这条是谁删的、占多少"，避免清空整个回收站误伤用户其他删除。

### 4. 会话与工作空间治理

```bash
python scripts/session_clean.py --report
python scripts/session_clean.py --clean-deleted --yes
python scripts/session_clean.py --keep "C:\code\a;C:\code\b" --yes
python scripts/session_clean.py --keep "C:\code\a;C:\code\b" --drop-data --yes --purge
```

`--clean-deleted` 清软删除会话的四类残留 + 无主 jsonl，并移除 `sessions` 表的已删行。
`--keep` 让 `workspaces` 表与 `workspace-display-names.json` 只剩保留名单；加 `--drop-data` 连会话数据一起清。
不加 `--yes` 只打印计划。改库前自动 `sqlite backup` 到 `.cleanup-<时间戳>/`。

## 处置顺序

1. **A 档先动**：缓存类（`CachedData`、`WebStorage/*/CacheStorage`、`CrashReport`、`Cache`、`Code Cache`、日志、剪贴板图、`file-history`）。
2. **B 档要用户点头**：非保留工作空间的会话与正文、旧版程序残留、diff 索引。逐项说清"删了失去什么"。
3. **C 档看场景**：`plugins/cache` 运行中删会坏插件，请用户退出后再清；`modify_backup` 删了不能撤销。
4. **D 档不动**：`binaries`、`blobs`、`workbuddy.db`、`security`、安装目录。
5. **最后收拾回收站**：前面所有"删除"多半只是移进回收站，空间没释放，必须用 `recycle_audit.py --purge` 或让用户自己清空。

## 收益核算

唯一口径是 `shutil.disk_usage` 前后差值。

- 同盘 `rename` = 0 释放
- 进回收站 = 0 释放
- 永久删除 = 真释放

若"移动量"远大于"释放量"，立刻查回收站。**不要拿移动量当释放量报给用户。**

## 已知坑位

详见 `references/已知坑位.md`，动手前必读。
