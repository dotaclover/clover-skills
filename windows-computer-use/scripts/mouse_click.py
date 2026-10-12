"""用坐标注入真实鼠标/键盘事件——光标会真的移动。

注意：坐标依赖屏幕分辨率/缩放/窗口位置，窗口移动后需重新取值。
若只要精确改文本、且不想动鼠标，请改用 uia_text.py。

依赖：pip install pyautogui
用法：
    python mouse_click.py --click 300 200
    python mouse_click.py --click 300 200 --key ctrl+w
    python mouse_click.py --key ctrl+w --key alt+f4
"""

from __future__ import annotations

import argparse

import pyautogui


def parse_combo(combo: str) -> list[str]:
    return [part.strip().lower() for part in combo.split("+") if part.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description="坐标注入真实鼠标/键盘事件")
    parser.add_argument("--click", nargs=2, type=int, metavar=("X", "Y"), help="移动光标到 (x,y) 并左键单击")
    parser.add_argument("--key", action="append", default=[], help="组合键，如 ctrl+w，可重复指定")
    parser.add_argument("--duration", type=float, default=0.3, help="光标移动耗时（秒）")
    args = parser.parse_args()

    if args.click:
        x, y = args.click
        pyautogui.moveTo(x, y, duration=args.duration)
        pyautogui.click()
        print(f"已移动到 ({x},{y}) 并单击")

    for combo in args.key:
        keys = parse_combo(combo)
        if not keys:
            continue
        pyautogui.hotkey(*keys)
        print(f"已发送组合键: {'+'.join(keys)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
