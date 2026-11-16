# 短剧通用工具脚本

从《失业华子的打工奇遇》实战中提炼的**方法级工具**，去掉了每部剧的硬编码设定，全部参数化。零依赖（除 Pillow），ffmpeg/ffprobe 需在系统 PATH。

| 脚本 | 职责 | 核心铁律 |
|---|---|---|
| `common.py` | 共用底座：ffmpeg 调用、实测静音段、PIL 叠字原语 | 脚本 import 它，别各写各的 |
| `subtitle_axis.py` | 本地静音检测定字幕轴（不用云端 ASR） | 轴取实测静音边界；连读按字数比例拆；每句≥0.45s |
| `text_overlay.py` | 通用中文叠字 PNG（描边、包围盒居中） | 数字与中文不加空格；`·` 两侧不留空格；居中按 getbbox 量 |
| `day_card.py` | 换日计数器卡「第N天·HH:MM」 | 每天早一分钟；day 0 写「前1天」 |
| `audio_mute.py` | 音轨区间静音（台词彻底删除） | 只静音人声不动画面；区间压在实测静音缝中央；字幕层同步删 |
| `verify.py` | 抽帧验收：解流、静音核对、切换点三帧拼图、近白像素 | 换日点抽三帧；静音区抽帧确认字幕也消失 |
| `grid_cut.py` | 一图流多宫格切单格 | 缝按实测给坐标，别按等分估 |

## 快速上手

```bash
# 1) 定字幕轴（先看发声段，再按逐字稿出 TSV 轴）
python subtitle_axis.py 原片.mp4                       # 只看发声段
python subtitle_axis.py 原片.mp4 --lines-file 台词.txt  # 出 起\t止\t文本

# 2) 叠中文字幕/日期卡
python text_overlay.py layer.png 720 1280 --text "月薪20000" --size 80 --y 1120
python day_card.py --out-dir cards/ --days 1 6 16 30 --start 09:00

# 3) 台词彻底删除（音轨静音，画面保留）
python audio_mute.py in.mp4 out.mp4 15.10:17.90 --verify

# 4) 验收
python verify.py final.mp4 --info --silence
python verify.py final.mp4 --joints 32.458 43.388 --out verify/

# 5) 一图流切图
python grid_cut.py grid.png --grid 3x3 --seams-x 1078,2156 --seams-y 1916,3832
```

## 依赖

- Python 3.9+
- Pillow（中文叠字）：`pip install Pillow`
- ffmpeg / ffprobe 在系统 PATH

## 字体

默认用 Windows 微软雅黑 `C:/Windows/Fonts/msyhbd.ttc`。换系统改 `common.py` 顶部 `FONT_BOLD` / `FONT_REG`。
