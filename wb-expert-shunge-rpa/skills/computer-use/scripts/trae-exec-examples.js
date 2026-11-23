// Trae Exec 沙箱示例片段 —— 仅在 Trae 的 Exec 工具里运行。
// 用法：把需要的片段复制进 Exec 的 code 参数（Exec 内的变量不会跨调用保留，需自己串接）。

// --- helper：所有调用都走它 ---
async function cu(tool_name, args) {
  return await tools.run_mcp({ server_name: "ide_mcp.config.ext.computer-use", tool_name, args });
}

// --- 1. 列出应用，找 pid / app_id ---
const apps = await cu("list_apps", {});
text(apps.content.filter(b => b.type === "text")[0].text);

// --- 2. 启动应用（app_id 来自 list_apps 的观测值）---
const launched = await cu("launch_app", { app: "Microsoft.WindowsNotepad_8wekyb3d8bbwe!App" });
text(launched.content.filter(b => b.type === "text"));

// --- 3. 观察（先只要语义树）---
const state = await cu("get_app_state", { pid, disableScreenshot: true });
text(state.content.filter(b => b.type === "text"));

// --- 4a. 语义操作：聚焦 + 用 set_value 精确写入（不受输入法影响，支持多行）---
await cu("perform_action", { pid, element_id: winId, action: "set_focus" });
await cu("set_value", { pid, element_id: docId, value: "trae work" });

// --- 4b. 坐标点击：会注入真实鼠标事件，光标真的移动 ---
// 坐标相对目标窗口；必须同时传目标窗口的 element_id。
await cu("get_app_state", { pid, disableScreenshot: false });   // 先建立截图坐标上下文
await cu("click", { pid, element_id: winId, x: 300, y: 200 });

// --- 4c. 关闭标签页：点不到标签栏时用 Ctrl+W ---
await cu("press_key", { pid, element_id: winId, key: "w", modifiers: ["ctrl"] });

// --- 5. 验证：以 UI 状态为证据 ---
const after = await cu("get_app_state", { pid, disableScreenshot: true, disableDiff: true });
text(after.content.filter(b => b.type === "text"));
