---
name: trae-computer-use
description: "Trae / TraeWork 环境下的电脑控制：用 computer-use MCP 的 UI Automation 操作本机 Windows 应用——查找/启动/聚焦窗口，点击控件、输入文字、关闭标签页与窗口。含 Trae 专属接入方式、工具清单、标准流程、Exec 示例片段、后端实测结论与报错排查。当在 Trae 中说「用电脑控制打开…」「帮我操作某个软件」「点一下 / 关掉这些标签页」「computer use」时使用。平台无关的通用 Windows 自动化知识见 windows-computer-use。"
agent_created: true
---

# Trae Computer Use（Trae 电脑控制）

**只在 Trae 环境适用**（依赖 Trae 的 MCP 集成与 Exec 沙箱）。Windows 平台无关的通用自动化知识见 `windows-computer-use`。

## 接入（Trae 专属）

server 名固定为 `ide_mcp.config.ext.computer-use`。先定义 helper，再用 Exec 做多步调用：

```js
async function cu(tool_name, args) { return await tools.run_mcp({ server_name: "ide_mcp.config.ext.computer-use", tool_name, args }); }
const apps = await cu("list_apps", {});
text(apps.content.filter(b => b.type === "text")[0].text);
```

`tools.run_mcp` / `text()` / `image()` 只存在于 Trae 的 Exec 沙箱；其他 AI 工具（Claude Code、Cursor、Codex CLI 等）无法照抄运行。

| 工具 | 用途 |
|---|---|
| `list_apps()` | 运行中应用（含 pid）+ 已安装应用（含 app_id） |
| `launch_app({app})` | 用 app_id 启动，返回里带 pid |
| `get_app_state({pid, disableScreenshot?, disableDiff?, max_depths?})` | 取 UI 树（可选截图） |
| `click / type_text / press_key / set_value / select_text / scroll / drag / perform_action` | 动作 |

## 标准流程

1. `list_apps` 找到目标 pid 或 app_id（一次即可，结果在本次会话内复用）。
2. 未运行 → `launch_app`；启动返回里已有 pid，直接用它。
3. `get_app_state`（先 `disableScreenshot: true` 只取语义树）。
4. 用 `element_id` 定位控件 → 执行动作 → 再次 `get_app_state` 验证结果。
5. 以下一步依赖的**真实观测**为准；窗口/结构变化会让旧 element_id 失效。

## Exec 示例片段

见 `scripts/trae-exec-examples.js`。常用几段：

```js
// 语义操作：切换窗口 + 用 set_value 精确写入（不受输入法影响，支持多行）
await cu("perform_action", { pid, element_id: winId, action: "set_focus" });
await cu("set_value", { pid, element_id: docId, value: "trae work" });
```

```js
// 坐标点击：会注入真实鼠标事件，光标真的移动
await cu("get_app_state", { pid, disableScreenshot: false });      // 先建立截图坐标上下文
await cu("click", { pid, element_id: winId, x: 300, y: 200 });     // 坐标相对目标窗口
```

## Trae 后端的实测结论

这些是本环境后端实测出来的，**不能当成通用结论**（通用部分见 `windows-computer-use`）：

- `element_id` 点击、`set_value` 走 UIA（Invoke/Value 模式），**不移动物理鼠标**。
- **坐标点击会注入真实鼠标事件**：实测点击前后系统光标 `(440,833) → (409,289)`，恰好等于窗口左上 + 相对偏移。
- `drag({fromX,fromY,toX,toY})` 可产生连续拖拽路径。
- 做不出"鼠标轨迹线 / 残影"那种可视化妆饰——那是客户端渲染的覆盖层，本工具链不产出；也没有连续 mousemove 原语。

## Trae 下的操作要点

### 文本输入
- 优先 `type_text`，但**输入法会污染**：实测输入 `trae work` 得到 `trae kkkk`。
- 需要精确文本时用 `set_value`（一次写入即得 `trae work`）；**多行内容也只能用 `set_value`**，`type_text` 打不出换行。

### 坐标点击前提
- 先 `get_app_state({disableScreenshot: false})` 建立截图坐标上下文。
- 坐标相对**目标窗口**；`click` 用坐标时必须同时传入目标窗口的 `element_id`。
- 非多模态 Agent 不要凭截图猜坐标；坐标不可靠时交给 `computer_use` 子代理。

### 权限弹窗
- 出现「XX 想要访问此设备 / 授予权限」类弹窗时**绝不点「允许」**（需用户确认）。
- 用「关闭」忽略或「阻止」拒绝，先处理掉弹窗再继续。

### 关闭标签页 / 窗口
- 优先点标签页上的「关闭标签页」按钮；标签栏在 UI 树里被折叠（`(N elements hidden)`）看不到时，聚焦窗口按 `Ctrl+W`。
- 注意：**关掉最后一个标签 = 关掉整个浏览器**（实测 Edge 全标签关闭后窗口消失，只剩后台残留进程）。

## 报错排查

- `No window found for pid`：目标窗口已不存在（常因上一步把它关掉了）。用 `list_apps` 复核，**不要重试同一动作**。
- `diff` / `no_change` 不是完整树；需要全量时用 `disableDiff: true`。
- 动作报 `No cached UI revision`：丢弃旧 element_id，重新 `get_app_state` 后再重试。

## 验证

- 完成以 UI 状态为准：窗口标题、内容、字符计数、标签数量等，必须能从 `get_app_state` 读到证据。
- 想拿"真实鼠标确实移动"的证据时，读写系统光标位置对比：

```powershell
powershell -File scripts/cursor_position.ps1
```
