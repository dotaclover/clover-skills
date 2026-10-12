# 版式实测与踩坑记录

这一节是**真跑出片 + 读像素量出来的**，不是照抄文档。文档在这个话题上有多处与事实不符，照抄必踩坑。

场景默认参考尺寸：竖屏 1080×1920。

---

## 逐像素量测的推荐值

| 元素 | 字段 | 实测值 | 量测依据 |
| --- | --- | --- | --- |
| 标题 | `displayTexts[0].attributes.y` | **200** | 白字顶边落在 212，视觉靠顶合适 |
| 标题 | `fontSize` | 76 | |
| 标题 | 折行上限 | 3 行 / 40 字 | 折行后受行数限制实际约 36 字 |
| 标题 | 单行宽度上限 | 画布 90%（竖屏 972px） | 超出会被两侧裁切 |
| 字幕 | `caption.attributes.y` | **1780** | 底框底边落在 1847，**离底 73px** |
| 字幕 | `caption.attributes.y` 安全上限 | **1829** | y=1830 → 离底仅 23px 已贴死；y≥1850 下半截被裁 |
| 字幕 | `fontSize` | 52 | 字幕框高度占用 ≈67px |

## 坑 1：标题不会自动折行

实测 21 字标题**直接横穿画面被两侧裁切**，没有任何警告。必须自己插 `\n` 断行：

```python
def wrap_title(title, font_size, canvas_w=1080, ratio=0.90, max_lines=3):
    limit = canvas_w * ratio
    lines, cur, cur_w = [], "", 0.0
    for ch in title:
        cw = font_size if ord(ch) > 0x2E80 else font_size * 0.5
        if cur and cur_w + cw > limit:
            lines.append(cur); cur, cur_w = ch, cw
        else:
            cur += ch; cur_w += cw
    if cur: lines.append(cur)
    lines = lines[:max_lines]
    # 均衡化：把最长行末字挪给最短行，直到行宽差 < 1 个字号
    while len(lines) > 1:
        widths = [len([c for c in l]) * font_size for l in lines]  # 简化示意
        mx, mn = widths.index(max(widths)), widths.index(min(widths))
        if mx == mn or len(lines[mx]) <= 1 or max(widths) - min(widths) <= font_size:
            break
        lines[mn] += lines[mx][-1]; lines[mx] = lines[mx][:-1]
    return "\n".join(lines)
```

## 坑 2：多行标题不居中

多行时**各行左对齐于同一个 x**，短行不会自动居中。解法是上面的「均衡断行」——让各行像素宽度尽量相等，左对齐的观感就接近居中。实测 21 字断成 722 / 684 两行，观感居中良好。

## 坑 3：字幕不传 x/y 就完全不显示

⚠️ **与文档矛盾**。文档说「不填 `attributes` 时默认画面居中、y 轴底部留白一号字高」，**实测成片里字幕完全不出现**。

必须 `topLeft: true` 且显式传 `x`、`y`：

```json
"caption": {
  "topLeft": true,
  "zIndex": 60,
  "attributes": {
    "x": 280, "y": 1780,
    "font": 6, "fontSize": 52, "fontColor": "#FFFFFF", "bold": true,
    "backgroundColor": "#1677FFCC", "radius": 12
  }
}
```

只传 `topCenter: true` + `zIndex`（无 attributes）→ 空白。只传 `topLeft` 不传 x/y → 空白。

## 坑 4：居中要自己算字宽

上游**没有 text-align 参数**，`x` 一律是文字块左上角。ASCII 半角和 CJK 全角宽度不同：

```python
def text_width(text, font_size, spacing=0.0):
    # CJK 及全角标点 ≈ 1.0 倍字号；ASCII 半角 ≈ 0.5 倍
    return sum((font_size + spacing) if ord(c) > 0x2E80 else (font_size * 0.5 + spacing)
               for c in text)

def center_x(text, font_size, spacing=0.0, canvas_w=1080):
    return max(0, int((canvas_w - text_width(text, font_size, spacing)) / 2))
```

实测：纯中文按 1.0 倍算出的 x 完全居中；「2026 产品发布会」若把数字也按 1.0 倍算，标题会明显偏右。

## 坑 5：字幕 x 要按「实际文案」算，不是按「17 字组件」算

文档说字幕组件宽度固定 17 个字。但**字幕是从 x 起左对齐排字，不是以 x 为左边界居中排列**。

- 按 17 字宽算得 `x=98` → 成片字幕**明显偏左**
- 按实际首句文案宽算得 `x=280` → 完全居中

所以要用播报文本的首句（在标点处断句）来估宽度。

## 坑 6：抽帧验证别用 `-ss`

`ffmpeg -ss 2` 会落在关键帧之间导致**输出空文件**。改用帧序号：

```bash
ffmpeg -y -i out.mp4 -vf "select=eq(n\,5)" -frames:v 1 -vsync 0 frame.png
```

## 成本提示

`displayTexts` / `caption` **不计费**，只有 `voiceTexts` 的语音时长计费。
做版式实验时把 `voiceTexts` 设为 `["你好"]` 即可产出约 0.76 秒的片子，**1 钻石一条**，标题随便测多长都免费。
