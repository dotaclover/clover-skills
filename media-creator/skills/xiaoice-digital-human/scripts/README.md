# 小冰数字人 API 示例脚本

所有脚本都是可直接运行的 curl 示例。**用法**：先设置环境变量，再执行。

```bash
export XIAOICE_KEY="你的订阅密钥"
export BASE="https://aibeings-vip.xiaoice.com"      # 或 https://openapi.xiaoice.com/vh
```

Windows PowerShell 用 `$env:XIAOICE_KEY="..."`。

## 脚本清单

| 文件 | 用途 | 是否产生费用 |
| --- | --- | --- |
| `01-list-avatars.sh` | 拉取公共形象列表 | 否（只读） |
| `02-avatar-detail.sh` | 查形象详情，拿 virtualHumanId / 姿态 / 声音 | 否（只读） |
| `03-materials.sh` | 拉花字模板 + 转场动画枚举 | 否（只读） |
| `04-generate-basic.sh` | **最简播报视频**（虚拟人 + TTS + 文本） | ⚠️ **是** |
| `05-generate-editor.sh` | **完整编辑器模式**（公式 + 字幕 + 文字 + 图片 + 背景 + 音乐 + 转场） | ⚠️ **是** |
| `06-poll-task.sh` | 轮询任务直到完成并下载成片 | 否（只读） |
| `07-list-tasks.sh` | 列出企业全部任务并汇总时长（对账用） | 否（只读） |
| `08-remove-tasks.sh` | 从任务列表移除任务 | 否（但见下方警告） |
| `09-avatar-train.sh` | 形象训练全流程（commit → 质检 → 启动 → 结果） | ⚠️ **是** |
| `10-voice-train.sh` | 声音训练全流程（commit → 结果） | ⚠️ **是** |
| `11-dialogue-video.py` | **双人对谈视频**（一个形象演两角色，左上/右下轮流说话） | ⚠️ **是** |

## ⚠️ 三条硬性注意

1. **`04` / `05` / `09` / `10` 会产生真实计费**。测试前务必确认账户额度，并且**不要用「金额刚好等于余额」的文本去测边界** —— 会让本该被拦的请求真的提交到上游（这条是实测踩过的坑）。要测限额拦截，请把余额先扣到 0，或用极短文本。

2. **`08-remove-tasks.sh` 不是取消任务**。实测结论：`remove` 后任务从列表消失，但 `detail` 查它仍是 `running`，**后台继续生成并计费**。小冰没有暴露真正的取消接口。它只能用来清理列表/隐藏任务。

3. **小冰的成片链接仅 24 小时有效**，且 2.5 系列还有下载次数上限。轮询到 `finished` 后必须立刻下载转存（`06` 脚本已包含下载）。

## 帮助脚本

| 文件 | 用途 |
| --- | --- |
| `gen_payload.py` | 生成带画布适配的提交 JSON（自动从姿态预览图解析宽高比），供 `05` 使用 |

```bash
python gen_payload.py \
  --avatar VHPVCW35N3M8DO0 \
  --text "大家好，这是一段测试播报。" \
  --out payload.json
```

它会自己调 `detailDigitalEmployee` 取 `virtualHumanId`、姿态和声音，并按预览图宽高比算好 `attributes`，避免虚拟人被拉伸变形。

## 关于域名

`https://aibeings-vip.xiaoice.com` 与 `https://openapi.xiaoice.com/vh` 实测功能等价，同一接口返回一致。后者是官方文档正式写明的域名前缀。建议做成配置项。
