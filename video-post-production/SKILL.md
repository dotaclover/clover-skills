---
name: video-post-production
description: "适用于既有视频二次加工：口播采访、会议讲座、产品展示、生活素材、录屏和已有成片的剪辑重排、多源拼接、原音保留或配音混音、横竖屏适配、可选字幕与遮挡、质量编码及显式体积压缩。不用于生成新视频、自动ASR或操作网页。"
agent_created: true
---

# 视频二次加工

当前版本：**1.0.0 开发稿**。按最初版统一管理，保留当前全部实现，不作功能回滚。仅在用户正式提交并明确指示后提升版本号；开发、测试、审计或打包均不自动升级。版本在正文明确，不使用未经完整元数据模式验证的顶层version字段。

## 默认与流程

1. 明确素材、受众、需要保留的内容、剪辑顺序、画布、音频、字幕及交付规格。参考 `references/需求分析.md`；不把非教程素材自动改成教程。
2. 默认完整视频、CRF 20质量模式、原音、第一源的分辨率与平均帧率。默认不放大画面、不启用体积目标、不加配音、字幕或步骤栏。多源默认统一到第一段源画布/帧率，contain等比缩小并补黑边；VFR会变为CFR而非逐帧保留源时间戳。
3. 使用隔离Python与已有FFmpeg/FFprobe。读取 `references/使用说明.md`；不自动安装依赖，不下载二进制或字体。无网络TTS时仅需Python标准库。
4. 执行 `probe` 分析源规格、时长、音轨及旋转标记；按需执行 `frames` 到全新目录。抽帧不等于场景识别；未检查画面/试听时不得声称已完成视觉或听感验收。render/frames拒绝旋转源，先由用户确认另存规范化方向副本。
5. 参照 `references/配置字段.md` 与 `assets/` 中JSON模板编写配置。segments省略即完整source；数组顺序就是成片顺序，可明确重排/重复/每段指定source。不把重复视为范围误差，但交付前说明是否有意重复。
6. 需要在线中文配音时先读取 `references/音色选择.md`，按语言与性别选择用户试听确认的四个首选音色；粤语采用粤语口语文案，不仅替换音色。未指定语言时依据内容确认，禁止用普通话音色合成粤语口语。默认保留原音；仅明确要求时采用replace、mix或mute。mix仅固定音量amix加限幅，无自动ducking。配音过长会裁切，短则补静音；不自动延长画面，需明确duration或自行裁剪录音。
7. 默认subtitle_mode为none；按要求选择sidecar或burn。显式subtitles相对加工后片段；subtitle_text仅按句长近似计时，非ASR/强制对齐。narration不会自动成为字幕。外部SRT导入尚未实现。
8. 按实际源画面设置pixels或normalized矩形遮挡，在缩放前执行，整段生效。字段移动时拆段；不声称自动脱敏。字体font可配置且必须本机可用。
9. 网络TTS仅在明确授权后传入 `--allow-tts-network`；只发送审核过的非敏感旁白文本到edge-TTS在线服务。没有授权时用本地voice_file。媒体读取仅允许file/pipe，不接受自由命令/滤镜，subprocess使用shell=False。
10. 执行render到全新目录，检查report与解码结果。仅显式 `encoding_mode: size` 搭配必填target_mb启用双遍上限控制；不承诺3–5MB，也不填充到下限。失败保留缓存，换全新目录重试。
11. 交付final.mp4、可选subtitles.srt、timeline.json、report.json；说明规格、字幕计时、音频处理、重复剪辑和限制。不得自动上传/发布/打包、删缓存或安装到用户技能目录。

## CLI

```bash
python scripts/video_pipeline.py --ffmpeg /path/to/ffmpeg --ffprobe /path/to/ffprobe probe /path/to/source.mp4
python scripts/video_pipeline.py frames /path/to/source.mp4 --output /path/to/new-frames --interval 2
python scripts/video_pipeline.py render --config /path/to/config.json --output /path/to/new-result
```

全局二进制参数须置于子命令之前。Windows使用正斜杠，含空格路径加双引号。以上python代表隔离解释器。

## 资源与边界

- `references/配置字段.md`：完整可执行字段与时间轴。
- `references/需求分析.md`：场景preset仅为文档决策层，非脚本自动预设。
- `references/升级说明.md`：当前开发说明、1.0.0版本管理与编码限制（保留文件名）。
- `references/使用说明.md`：运行、输出、验收。
- `references/tests报告.md`：真实测试及未覆盖项，不是安全审计。
- `references/安全审计报告.md`：当前1.0.0开发稿全部包内文件的11步静态审计、关键行号、授权边界与外部依赖风险。
- `assets/config.example.json`及其他JSON：原音质量、口播字幕、混音、显式限体积、竖屏、多源模板。
- `requirements.txt`：仅可选edge-TTS依赖。脚本不执行pip。

不提供ASR、自动场景切分、OCR、动态遮挡、自动ducking、步骤栏、外部SRT导入、HDR/色彩管理保证、精确无缝多机位剪辑。质量模式片段重编码一次并copy拼接，size额外双遍；未实现所有条件下的源流复制优化。只读可信本地素材与配置；协议白名单不是文件系统沙箱。
