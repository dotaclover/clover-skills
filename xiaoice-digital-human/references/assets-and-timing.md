# 素材准备、媒体资源限制与时长标定

---

## 素材准备

**官方没有素材上传接口**，所有素材都用 `mediaUrl` 直接引用现成 URL。这意味着素材必须**公网可访问**且是直链（不能带鉴权、不能是页面地址）。

| 素材类型 | 字段 | 格式与上限 |
| --- | --- | --- |
| 背景音乐 / 场景音乐 | `backgroundMusic.mediaUrl` | MP3、WAV，≤50MB |
| 背景图片 | `backgroundImage.mediaUrl` | JPG、PNG、GIF，≤10MB |
| 文字素材 | `displayTexts[].content` | 纯文本，无上传 |
| 图片素材 | `displayImages[].mediaUrl` | JPG、PNG、GIF，≤10MB |
| 视频素材 | `displayVideos[].mediaUrl` | MP4，≤300MB |
| 自定义音频（替代 TTS） | `scenes[].voiceUrl` | MP3、WAV，≤100MB |
| 自定义字体 | `attributes.fontPath` | 字体文件如 `https://xxx.ttf` |
| 形象/声音训练素材 | `trainingVideoUrl` / `trainingAudioUrl` | 也必须是公网直链 |

自建服务时，用 Nginx 反代一个 `/uploads/` 公开目录即可满足。

## 媒体资源限制（重要）

`displayImages` / `backgroundImage` 的 `mediaUrl` **只接受小冰自家 CDN 域名的图片**：

| 图片源 | 结果 |
| --- | --- |
| `virtualman.oss-cn-beijing.aliyuncs.com/...` | ✅ 200 |
| `images.unsplash.com/...` | ❌ 410 媒体资源url错误 |
| `picsum.photos/...` | ❌ 410 媒体资源url错误 |

也就是说**要给视频加背景/贴图，必须先把图片传到小冰的 OSS**。
工作台的 `/api/upload` 走的是「本地存储 + 公网 URL」路线，需要配 `PUBLIC_BASE_URL`，
**但这条路产出的 URL 不是小冰 CDN 域名，上游同样会 410**。

> 结论：当前账号下**没有可直接使用的背景图能力**。可行的只有：
> ① 纯白底；② 用小冰 CDN 上已有的图（如形象预览图）当贴图，但它是前景图层，盖住人不好看。
> 若要真正的背景，需要向小冰申请素材上传接口 / OSS 直传能力。

## 字段名速查（易错）

| 素材 | 正确的资源字段 | 错误写法 |
| --- | --- | --- |
| `scene.backgroundImage` | `{mediaUrl, zIndex}` | `{url}` / `{imageUrl}` → 410；直接传字符串 → 407 |
| `displayImages[]` | `{mediaUrl, zIndex, attributes}` | `{url}` → 410 |
| `creationDetail.backgroundMusic` | `{mediaUrl, volume, speed, loop}` | — |

---

## 时长预估标定（实测）

`videoDurationMilliseconds` 与实际文本的关系，实测三组样本：

| 文本类型 | 字数 | 实际时长 | 实际语速 |
| --- | --- | --- | --- |
| 真实中文播报（含标点） | 175 | 33.68 s | 5.20 字/秒 |
| 连续重复字（极端下限） | 400 | 128.72 s | 3.11 字/秒 |
| 连续重复字（极端下限） | 3000 | 967.16 s | 3.10 字/秒 |

结论：**不要用「字数 ÷ 3」这种粗估去卡额度**。若要预扣，按 3 字/秒（实测最慢）计算才安全；正常文本会明显偏保守，多余部分必须退还。真正准确的时长只有 `videoDurationMilliseconds` 说了算，结算一律以它为准。
