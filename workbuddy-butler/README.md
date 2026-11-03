# WorkBuddy管家

管 WorkBuddy 本机空间：盘清占用、分类打标、备份后回收，只删可再生的东西。

## 类型

Agent 型（单个 AI 专家）

## 功能

- **空间台账**：把 `~/.workbuddy`、`%APPDATA%\WorkBuddy`、安装目录、旧版本残留、Windows 回收站一起盘清，按 A（可直删）/ B（需确认）/ C（慎动）/ D（禁动）四档打标。
- **会话数据治理**：直读 `workbuddy.db`，区分存活与软删除会话，按工作空间归组算出 `modify_backup`、`changes-detail`、`file-tree-manifests`、`projects/*.jsonl` 各占多少。
- **工作空间管理**：按保留名单裁剪 `workspaces` 表与 `workspace-display-names.json`。
- **安全删除**：识别本机的 safe-delete 垫片，用 `SHFileOperationW` 做真删除，避免"删了但空间没少"。
- **回收站取证**：解析 `$Recycle.Bin/$I*` 元数据还原原始路径，按特征精确永久删除。
- **收益核算**：以 `disk_usage` 前后差值为唯一口径，分开报"移动量 / 进回收站量 / 真正释放量"。

## 使用示例

- 先扫一遍WorkBuddy占了哪些空间，按能不能安全删分类，给我一份清单
- 只保留我指定的几个工作空间，其余的连记录带文件清掉
- 我删了会话但空间没变，帮我查出到底是什么占着

## 附带技能

`skills/workbuddy-disk-audit/`，四个脚本：

| 脚本 | 用途 |
|---|---|
| `scan_space.py` | 出空间台账（支持 `--json`） |
| `purge.py` | 永久删除，绕过 safe-delete 垫片 |
| `recycle_audit.py` | 回收站取证 / 精确永久删除 |
| `session_clean.py` | 软删除会话残留清理、工作空间记录裁剪 |

`references/已知坑位.md` 记录了 10 个真实踩过的坑，动手前必读。

## 头像

头像已自动生成在 `avatars/workbuddy-butler.png`（512×512，375KB）。如需替换：
- 格式：PNG（推荐）或 JPG
- 尺寸：512×512 px
- 大小：单张不超过 500KB

## 安装

专家包目录：`~/.workbuddy/plugins/marketplaces/my-experts/plugins/workbuddy-butler/`

注册后在【专家中心 - 我的专家】可见：

```bash
python scripts/register_expert.py <expert-dir>
```

## 打包分享

```bash
python scripts/package_expert.py <expert-dir>
```
