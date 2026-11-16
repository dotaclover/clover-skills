---
name: xingqiao-media
description: 接入星桥多模态供应商的图片、视频、询价、任务查询与对账接口；按当前账号能力和任务预算执行，隔离配置、状态和供应商协议。
agent_created: true
---

# 星桥多模态接入

星桥供应商根地址为 `https://api.novqiao.com`。这不是官方模型直连协议；型号、权限、价格与参数按当前服务契约确认，不根据历史账号推断。

## 接收任务

取得 `project_root`、实际 `skill_root`、私有配置路径、账号/项目标识、独立 `state_dir`、`output_dir`、目标规格、数量、预算币种及上限、结算合约、授权范围。缺项先问，不固定选最便宜模型。角色分工由当前团队指定。

仅写代码时使用占位配置。真实查询需要账号授权；上传素材、创建任务、回调部署、收费提交分别确认。失败不自动重提，先查原任务与账单。

## 配置与离线检查

以下 Bash 示例先将 `SKILL_ROOT` 设置为实际安装的本技能目录，不要求工作区具有 expert/skills 布局。`PRIVATE_CONFIG`、`STATE_DIR`、`OUTPUT_DIR` 均由当前任务提供，不复用其他账号状态。

```bash
python "$SKILL_ROOT/scripts/xq.py" --config "$PRIVATE_CONFIG" --state-dir "$STATE_DIR" self-test
python "$SKILL_ROOT/scripts/xq.py" --config "$PRIVATE_CONFIG" --state-dir "$STATE_DIR" image --prompt "白色陶瓷杯" --model "<当前型号>" --dry-run
```

全局 `--config`、`--state-dir`、`--no-proxy` 放在子命令前。默认兼容 `~/.xingqiao/config.json`；显式配置默认将状态放其同目录，指定 `--state-dir` 可进一步隔离。多账号必须使用不同配置/状态目录。支持授权环境变量 `XINGQIAO_API_KEY`，优先于配置值；不自动保存环境密钥。`init` 明文配置仅用于私有目录，不提交 Git。`show` 打码。`self-test` 和 `--dry-run` 不读取账号配置、不联网。

默认尊重系统/环境代理，仅明确需要直连时使用 `--no-proxy`。不关闭 TLS 校验。原始输出与成品拒绝覆盖已有文件；更换输出路径，不用重提生成解决下载冲突。任务状态文件按同一任务更新、账本追加属于内部状态操作。

## 执行流程

1. 在授权下 `models --kind image|video` 查当前能力。图片使用 `quote --prompt ... --model ...` 询价；有本地参考素材时询价可能先上传，也需上传授权。视频查看目录报价及参考视频价格表。
2. 确认模型、输入权利、参数组合、数量、预算与币种。5 秒、720p、1K 等均只是规格示例，不是默认承诺。
3. `image` / `video` 只提交一次，显式指定 `--model`、目标规格及 `--out-dir "$OUTPUT_DIR"`；保存任务 ID。图片使用 Idempotency-Key，视频使用 client_task_id，具体去重期限按供应商参考确认。
4. 有限轮询，202 只代表受理。视频等待 `terminal` 与 `next_action:read_result`；超时保留原任务并用 `status --kind ... --task-id ...` 查询，不当作取消。
5. 下载并实测尺寸、时长、编码、声音与内容。签名链接不带 Key，认证下载仅向原供应商发送 Key，不转发到存储域。
6. 用 `ledger` 查看原始 `cost_usd`，`reconcile` 按已记录任务逐条查询，不证明遗漏任务已发现。账本默认不推断人民币；仅在合约明确时传 `ledger --rate <比例>` 作估算，最终结算以当前账单与合约为准。

## 接口与待核验

- 图片字段、状态、错误、幂等与回调见 [image-api.md](references/image-api.md)。其中批查 POST 与其他资料 GET 存在冲突，当前契约待确认，不猜方法；脚本对账使用已明确的单任务 GET。
- 视频 video-v2 专属字段与状态见 [video-api.md](references/video-api.md)，不与 `/v1/videos` 混用。
- 回调由当前部署决定。需要受控公网 HTTPS、验签、防重放、去重与写入授权；未配回调时轮询，不禁止其他项目合法使用回调。
- 目录可见不证明生成能力、价格或审核通过。历史迁移、任务号、账单、速度与模型快照不作为当前账号事实；按账号私有记录保存，不固化在通用技能。

## 交付

报告 provider、模型与参数、任务 ID、真实状态、实际规格、成品路径、原始用量/预计费用/结算币种、账单依据和未验证项。错误保留脱敏代码与消息，不输出密钥、签名 URL 或私人素材。离线测试位于 `scripts/test_xq.py`，只使用临时目录与 mock，不发送生成请求。
