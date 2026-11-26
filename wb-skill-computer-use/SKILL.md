---
name: wb-skill-computer-use
display_name: Windows电脑控制
display_name_en: Windows Computer Use
description: Windows上操作桌面应用的两种方式——内置GUI控制（截图+坐标点击，走虚拟桌面授权）与无感窗体消息（FindWindow+PrintWindow+PostMessage，不抢焦点不移动鼠标）。以WorkBuddy领取每日100积分为完整示例，附两个可跑脚本。涉及Windows桌面自动化、重复点击、后台操作、GUI打卡、无法复用API的客户端操作时使用。
description_zh: Windows桌面自动化双方案：GUI控制适合未知界面探索，需虚拟桌面授权；窗体消息适合已知坐标的重复操作，不干扰用户。附WorkBudBuddy领积分实战脚本。
description_en: Two Windows desktop automation approaches - GUI agent control for exploration and Win32 window messages for silent repeatable clicks. Includes working scripts for WorkBuddy daily point claim.
examples_zh:
  - '帮我自动在WorkBuddy领每日积分'
  - '每天点某个客户端按钮，别打扰我用电脑'
  - '这个Windows软件没有API，怎么自动操作'
examples_en:
  - 'Automate daily point claim in WorkBuddy'
  - 'Click a desktop app button without stealing focus'
  - 'How to automate a Windows app with no API'
version: 1.0.0
author: 独立开发者
agent_created: true
---

# Windows电脑控制：两种方案

Windows桌面自动化只有两类需求，对应两种方案。**别混用**：探索界面用方案A，已知坐标的重复操作用方案B。

| 维度 | 方案A：内置GUI控制 | 方案B：无感窗体消息 |
|---|---|---|
| 手段 | 内置computer-use，截图+VLM定位+真实鼠标点击 | `FindWindow`+`PrintWindow`+`PostMessageW` |
| 是否抢焦点 | 是（独立桌面可隔离） | 否 |
| 是否动鼠标 | 是 | 否 |
| 首次授权 | 需要：虚拟桌面UAC+Windows登录密码 | 不需要 |
| 界面未知时 | 能自己看图找按钮 | 不行，必须预先知道坐标 |
| 后台被遮挡 | 需切到目标窗口 | 不受影响，`PrintWindow`直接读窗口DC |
| 适合 | 一次性探索、流程不明、跨应用跳转 | 每日打卡、固定按钮、不能打扰用户的场景 |
| 依赖 | WorkBuddy内置能力 | Python标准库ctypes，零第三方包 |

**结论**：用户说"别干扰我操作电脑"→直接用方案B。用户说"我不知道点哪"→先用方案A摸清界面，把坐标记下来，再用方案B固化成脚本。

## 方案A：内置GUI控制

调用内置computer-use能力，由GUI agent截图、识别、点击。

要点：

- 先`gui_list_windows`找目标窗口，再`create_task`传`window_id`。
- 任务描述必须写清三部分：分步目标、边界（不许碰什么）、异常处理（没反应就如实记录，别重试）。不要给像素坐标，让agent自己看图。
- Windows上默认走独立桌面（child_session）。首次使用要用户完成一次性授权：输入框上方「请求协助」卡片→「去授权」→UAC点「是」→必要时输一次Windows登录密码。
- 授权卡住时调用`gui_setup_permission`等待，**不要自己提权，也不要降级到主桌面**。
- 用户明确拒绝授权时，别反复劝；转而用方案B。

示例任务描述：

```
目标：在WorkBuddy客户端领取每日积分。点击左下头像，点Buddy加油站，
在左下气泡中点「领取100积分」。
边界：只做打卡，不改设置、不点其它菜单、不输入文字。
异常处理：某步点击无反应就如实记录并结束，不要重试或换途径。
完成后报告是否领取成功及最终积分状态。
```

配套脚本`scripts/gui_click.py`是方案A的"裸脚本版"：不走GUI agent，用`SetCursorPos`+`mouse_event`真实点击。会移动鼠标、抢焦点，只适合用户不在电脑前时用。

```bash
python scripts/gui_click.py info                 # 列窗口、句柄、矩形
python scripts/gui_click.py shot --out cur.png   # 全屏截图（PNG，无第三方库）
python scripts/gui_click.py click 405 1650       # 真实鼠标点击（物理坐标）
python scripts/gui_click.py scroll -120 500 800  # 滚动
```

## 方案B：无感窗体消息

核心三板斧：

1. `FindWindowW` 拿窗口句柄——按窗口标题找，不依赖前台。
2. `PrintWindow(hwnd, memDC, 2)` 从窗口DC直接画到内存位图——不受其它窗口遮挡，不用截屏。
3. `PostMessageW(hwnd, WM_LBUTTONDOWN/UP, ...)` 投递鼠标消息——光标不动，焦点不抢，用户无感。

配套脚本`scripts/wb_checkin.py`：

```bash
# 1. 探窗口和DPI，确认坐标基准
python scripts/wb_checkin.py probe

# 2. 状态只能作为亮度参考，不代表领取状态
python scripts/wb_checkin.py status

# 3. 对照最新截图确认按钮文字、位置后，指定实际屏幕坐标投递一次点击
python scripts/wb_checkin.py click --center 405,1650

# 4. 再截图核实结果；run已禁用自动点击
python scripts/wb_checkin.py probe --shot after.png
```

### 坐标从哪来

这是方案B唯一的麻烦事。流程：

1. `probe` 确认屏幕物理分辨率和DPI缩放。Windows高DPI下必须`SetProcessDPIAware()`，否则`GetSystemMetrics`返回逻辑像素、坐标全错。
2. 用`gui_click.py shot`或`wb_checkin.py probe --shot path.png`截图，找到按钮的物理坐标。
3. 客户区原点用`ClientToScreen`确认。WorkBuddy最大化窗口的物理原点是(0,0)，屏幕坐标即客户区坐标；别的窗口要减去原点偏移。
4. 以截图实际文字判断状态，亮度只能参考，不能据此认定已领取或可领取。

### 状态判断

亮度不能确认按钮文字、领取状态或点击结果。每次都先看后台截图，核对实际按钮及坐标；点击后重新截图，以明确成功提示、已领取文字或积分变化为证据。无法确认则报告状态不明。

## 实战：WorkBuddy每日100积分

界面路径：左下Buddy加油站卡片。2026-11-26实测卡片显示“每日可领100积分”，按钮实际文字为“立即领取”，不是“领取100积分”。当卡片和按钮明确对应每日积分时，核对坐标后可点击“立即领取”；不要因按钮不含数字而跳过。页面可能变化，不能仅凭旧截图操作。

物理分辨率3072×1920（200% DPI，任务栏占底部96px），客户区原点(0,0)。坐标：

| 元素 | 物理坐标 | 说明 |
|---|---|---|
| 左下头像 | (50,1770) | **不要点**。点头像弹设置菜单（意见反馈/检查更新/退出登录），会挡住气泡 |
| 气泡第一页分页点 | (60,1680) | 定位到Buddy加油站 |
| 气泡第二页分页点 | (93,1680) | 做任务赢积分好礼 |
| 领取按钮区域 | (330,1630,150,40) | 采样亮度用 |
| 领取按钮中心 | (405,1650) | 投递点击用 |

历史坐标仅供参考，不能直接照搬。脚本的`run`已禁用自动点击；先截图核对，再用`click --center x,y`投递，最后截图核实。

## 边界与坑

- 只做Windows。macOS没有`FindWindow`/`PostMessage`，走GUI方案。
- Electron客户端（WorkBuddy、VSCode等）没有原生Win32控件树，`SendMessage(BM_CLICK)`对网页渲染的按钮无效；但`PostMessage`鼠标消息有效，已实测。
- 无PowerShell `Add-Type` / `Reflection.Assembly`时别硬试，安全策略会拦。纯Python ctypes是干净的路子。
- `computer-use`如果返回`authorization_required`，那是虚拟桌面的授权，跟"已经给过电脑控制权限"是两码事。用户拒绝就转方案B，别反复引导。
- 坐标绑定分辨率和布局。改了显示器缩放、窗口尺寸或客户端版本后，重新`probe`取坐标。
- 方案B不检查"气泡是否可见"。如果气泡被关掉，`PrintWindow`读到的是背景，亮度可能误判。跑之前确认气泡常驻，或先`probe --shot`看一眼。
