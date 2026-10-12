# 读当前系统光标位置，用于验证 Trae 坐标点击是否真的移动了鼠标。
# 用法：powershell -File scripts/cursor_position.ps1
# 技巧：坐标点击前后各跑一次，对比 X/Y 是否变化。
Add-Type -AssemblyName System.Windows.Forms
$p = [System.Windows.Forms.Cursor]::Position
"X=$($p.X) Y=$($p.Y)"
