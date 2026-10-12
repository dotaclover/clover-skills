# 多角色对话视频（双人对谈）

把一个形象当一个人用太浪费。**同一条视频里演一场双人对谈**是这套 API 最容易被忽略的能力，实测可行，方案如下。

---

## 核心限制与对策

| 限制（实测） | 对策 |
| --- | --- |
| 一个 `scene` 只能有一个 `virtualHuman`（传数组报 `407 非法的请求体`） | 用 `scenes[]` 逐句切场景，**每句都是独立场景** |
| 逐场景切换会让虚拟人「原地变脸」，观感等于一个人在自问自答 | **给每个角色分配固定坐标**（A 左上、B 右下），场景切换时只有人变、位置不变 |
| 账号内可能只有一个男性形象 | 用**同一形象的两种姿态**当两个人（`postureInfos` 常有 4–44 个，如「潮人-聆听」「老板-聆听」），视觉差异明显 |
| 形象自带音色可能只有一种 | 音色池里有**公共音色** `101-wenyou`（男）、`101-*` 系列，任意形象都可用；账号内音色大多也支持 `zh-CN / zh-HK / en-US` 三语，念英文无需换音色 |

## 坐标模板（竖屏 1080×1920，两人各占一角）

```python
BOX_W, BOX_H = 430, 764        # 720×1271 姿态图等比缩放到 430 宽
TOM_BOX   = (55, 470)          # 左上
JERRY_BOX = (595, 990)         # 右下
```

每个场景里：

```python
scene = {
    "virtualHuman": {
        "virtualHumanId": VID,
        "virtualHumanPostureId": POS_TOM if who == "Tom" else POS_JERRY,
        "zIndex": 20,
        "attributes": {"x": TOM_BOX[0], "y": TOM_BOX[1], "width": BOX_W, "height": BOX_H},
    },
    "tts": {"voiceId": VOICE, "rate": 1, "pitch": 1, "volume": 50},
    "voiceTexts": [text],
    "caption": { ... },                      # 每句自己的字幕，位置固定
    "displayTexts": [                        # 两个名牌常驻，说话方高亮
        {"content": "Tom",   "zIndex": 30, "attributes": {name_attrs(C_TOM if who=="Tom" else C_DIM)}},
        {"content": "Jerry", "zIndex": 31, "attributes": {name_attrs(C_JERRY if who=="Jerry" else C_DIM)}},
    ],
}
```

名牌的 zIndex 必须一个 30、一个 31 之类**互不相同**，否则 `420 图层序号错误`。

说话方高亮（`#FFE400` 黄 / `#4DD0FF` 蓝），非说话方压暗成 `#8C97A6`——观众一眼知道谁在说。

## 实测效果

4 场景 × 约 4 秒 ≈ **15 秒**，11 MB，1080×1920。同一形象的「潮人装」与「西装」两个姿态分别出现在左上、右下，切场景时人物不同、位置不动，能明确读出「两个人在对话」。

## 成本

每个场景的 `voiceTexts` 独立计费，总时长 = 各场景时长之和，与单场景等字数成本相同。**字幕、名牌、坐标全部免费**，只有语音计费。

---

## 背景图不可用（实测，影响对谈版式）

`scene.backgroundImage` **不受 zIndex 影响**：实测把它的 zIndex 设为 5/10/90、虚拟人设为 3/20/50，成片**完全相同**——图片恒定盖在虚拟人之上，等于一层**前景遮罩**，不是背景。官方文档称其为「场景背景图（自动拉伸覆盖全屏）」，**与实测不符**。

所以想给对谈/播报视频加「背景」，**不要用 `backgroundImage`**：

- 可行做法一：用 `displayImages`（图片素材，zIndex 可小于虚拟人）垫底；
- 可行做法二：干脆保留纯白/纯色底。

（`displayImages` 本身还有 CDN 域名限制，见 `assets-and-timing.md`。）

## 字幕词中截断（英文长句必踩）

上游成片字幕是**按语音切句 + 按字符宽度硬换行**，**不在词边界断**。英文长句会出现：

```
sounds nice. Are you enjoying the s
lower pace
```

中文因为每字等宽不太明显，**英文尤其难看**。缓解办法：把长句拆成两个较短的 `voiceTexts` 项，或把关键停顿写成分句标点让上游切得短一些。

> 实测确认：`voiceTexts` 里手插 `\n` **不会**改变成片字幕的换行位置。
> 对照组 `"...enjoying the slower pace"` 与 `"...enjoying\nthe slower pace"` 的成片字幕
> **完全一致**，都是 `the s / lower pace`。字幕由上游按语音重新切句生成，客户端无法干预换行。
