---
name: windows-computer-use
description: "Windows 桌面自动化通用知识（平台无关）：用 UI Automation 语义操作或坐标输入注入来驱动任意 Windows 应用——点击控件、输入文本、关闭标签页与窗口。不依赖特定 AI 平台，适用于任何能驱动 UIA / 注入输入的 AI 工具或自研脚本（pywinauto / uiautomation / pyautogui / PowerShell）。当任务需要通用的「操作 Windows 软件」「点按钮 / 关标签页」时使用。Trae 环境里的具体调用方式见 trae-computer-use。"
agent_created: true
---

# Windows Computer Use（通用）

Windows UI 自动化的**平台无关**知识。这里只讲"在 Windows 上怎么操作界面"，不绑定任何 AI 平台。Trae 环境下的具体工具调用见 `trae-computer-use`。

## 适用范围

| 场景 | 是否适用 |
|---|---|
| 任意能驱动 UI Automation 的 AI 工具 | ✅ 把下面的要点套到它自己的工具调用上 |
| 自研脚本（pywinauto / uiautomation / pyautogui / PowerShell） | ✅ 直接用 `scripts/` 里的脚本或对应 API |
| 非 Windows 平台 | ❌ |

## 两条技术路线

1. **语义操作（UIA）**：取控件树，按控件的句柄/属性直接调用 Invoke（点击）、Value（写文本）、Focus 等模式。
   - 优点：稳定，不依赖分辨率与坐标，窗口移动也不失效。
   - 特点：**不移动物理鼠标**，界面直接变化，观感像"内容凭空出现"。
   - 实现：`pywinauto`、`uiautomation`、COM `IUIAutomation`。
2. **坐标输入注入**：定位屏幕坐标后注入真实鼠标/键盘事件（`SendInput` / `mouse_event`）。
   - 特点：**光标会真的移动**，观感接近人工操作。
   - 缺点：依赖分辨率/缩放/窗口位置，窗口一动就作废。
   - 实现：`pyautogui`、`pywin32 SendInput`、AutoHotkey。
   - 注意：**是否真的移动光标取决于具体实现的后端**。Trae 后端的实测结论见 `trae-computer-use`。

## 通用实践要点

### 文本输入
- 模拟键盘输入可能被**输入法拦截污染**（合成字符被 IME 重新转换）。实测：想输入 `trae work`，结果得到 `trae kkkk`。
- 需要精确文本时优先走 UIA 的 **Value 模式直接写控件**（如 `set_text`），一次到位、不受输入法影响。
- 多行/带换行的文本同样只能走 Value 模式；模拟按键通常打不出换行。

### 权限弹窗
- 出现「XX 想要访问此设备 / 授予权限」类弹窗时，**绝不自动点「允许」**（属于需要用户确认的操作）。
- 用「关闭」忽略或「阻止」拒绝，先处理掉弹窗，再继续主流程。

### 关闭标签页 / 窗口
- 优先点标签页上的「关闭标签页」按钮。
- 定位不到标签栏时，聚焦窗口后发 `Ctrl+W`。
- **关掉最后一个标签 = 关掉整个浏览器**（窗口随之消失，只剩后台残留进程）。

### 验证
- 完成以**界面状态**为准（窗口标题、内容、字符计数、标签数量），不要凭"动作已执行"就宣称完成。

## 脚本

### `scripts/uia_text.py` —— 语义操作，精确写入文本

用 UIA 的 Value 模式写控件，不受输入法影响，支持多行。依赖 `pywinauto`。

```bash
pip install pywinauto
python scripts/uia_text.py --title-re ".*Notepad" --text "trae work"
python scripts/uia_text.py --title-re ".*Notepad" --control Document --text "第一行\n第二行"
```

### `scripts/mouse_click.py` —— 坐标注入，光标真的移动

依赖 `pyautogui`。

```bash
pip install pyautogui
python scripts/mouse_click.py --click 300 200           # 移动光标到 (300,200) 并单击
python scripts/mouse_click.py --click 300 200 --key ctrl+w
python scripts/mouse_click.py --key ctrl+w --key alt+f4
```

### `scripts/cursor_position.ps1` —— 读系统光标位置

用于验证"坐标注入是否真的移动了鼠标"。

```powershell
powershell -File scripts/cursor_position.ps1
```

## 示例：语义操作（pywinauto）

```python
from pywinauto import Desktop

win = Desktop(backend="uia").window(title_re=".*Notepad")
win.set_focus()
edit = win.child_window(control_type="Document")
edit.set_text("trae work")     # Value 模式：精确、不受输入法影响
```

## 示例：坐标注入（pyautogui）

```python
import pyautogui
pyautogui.moveTo(300, 200, duration=0.3)   # 真实移动光标
pyautogui.click()
pyautogui.hotkey("ctrl", "w")              # 关闭当前标签页
```
