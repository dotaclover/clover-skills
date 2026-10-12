"""用 UI Automation 的 Value 模式向 Windows 应用精确写入文本。

走语义操作（UIA），不移动物理鼠标；因绕过模拟键盘，输入法不会污染内容，且支持多行。

依赖：pip install pywinauto
用法：
    python uia_text.py --title-re ".*Notepad" --text "trae work"
    python uia_text.py --title-re ".*Notepad" --control Document --text "第一行\n第二行"
"""

from __future__ import annotations

import argparse
import sys

from pywinauto import Desktop


def main() -> int:
    parser = argparse.ArgumentParser(description="用 UIA Value 模式精确写入文本")
    parser.add_argument("--title-re", required=True, help='窗口标题正则，如 ".*Notepad"')
    parser.add_argument("--text", required=True, help="要写入的精确文本，支持 \\n 换行")
    parser.add_argument("--control", default="Document", help="目标控件 control_type，默认 Document")
    args = parser.parse_args()

    text = args.text.replace("\\n", "\n")

    win = Desktop(backend="uia").window(title_re=args.title_re)
    if not win.exists():
        print(f"未找到匹配窗口: {args.title_re}", file=sys.stderr)
        return 1

    win.set_focus()
    control = win.child_window(control_type=args.control)
    control.set_text(text)  # Value 模式：精确、不受输入法影响
    print(f"已写入 {len(text)} 个字符")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
