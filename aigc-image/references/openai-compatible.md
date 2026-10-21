# OpenAI 兼容图片接口 · 完整参数

> 这里的字段以 OpenAI Images API 为基准。OpenAI 兼容格式的生图接口——国内大厂、独立服务商、自建服务——大多照抄这套字段，但**支持子集各不相同**：字段被忽略通常不报错，只是没生效。跑通最小字段后，一次只加一个参数。

## 路由

| 用途 | 方法 | 路径 | Content-Type |
|---|---|---|---|
| 文生图 | POST | `{base}/images/generations` | `application/json` |
| 图生图 / 局部重绘 / 多图合成 | POST | `{base}/images/edits` | `multipart/form-data` |
| 变体（老模型） | POST | `{base}/images/variations` | `multipart/form-data` |
| 列模型 | GET | `{base}/models` | — |

`{base}` 一般以 `/v1` 结尾。`{base}/models` 是最便宜的健康检查：能返回 `data[].id` 就说明地址和 Key 都对。

## `/images/generations` 字段

| 字段 | 类型 | 取值 | 说明 |
|---|---|---|---|
| `model` | string | 供应商模型名 | 必填。不同供应商命名差异极大，只认 `/models` 返回的名字 |
| `prompt` | string | 文本 | 必填。多数模型上限约 32000 字符，实际写 200–800 字更稳 |
| `n` | int | 1–10 | 默认 1。部分模型强制 1 |
| `size` | string | 见下方尺寸表 | 不给则用模型默认 |
| `quality` | string | 新模型 `low`/`medium`/`high`/`auto`；DALL·E 3 是 `standard`/`hd` | 影响耗时与费用 |
| `response_format` | string | `url` / `b64_json` | 不给时：DALL·E 默认 `url`，较新的图像模型默认 `b64_json` |
| `style` | string | `vivid` / `natural` | **仅 DALL·E 3**，其他模型忽略 |
| `background` | string | `transparent` / `opaque` / `auto` | 需要透明底时配 `output_format` 为 `png` 或 `webp` |
| `output_format` | string | `png` / `jpeg` / `webp` | 默认 `png` |
| `output_compression` | int | 0–100 | 仅 `jpeg` / `webp` 生效，默认 100 |
| `moderation` | string | `low` / `auto` | `low` 放宽审核，是否支持看供应商 |
| `partial_images` | int | 0–3 | 配合 `stream: true` 出中间预览图，多数服务不支持 |
| `stream` | bool | `true` / `false` | 流式返回事件，非流式服务会直接 400 |
| `user` | string | 稳定标识 | 供应商侧溯源与限流归因 |

### 尺寸支持（以官方口径为准，各家可能更宽或更窄）

| 模型族 | 可用尺寸 |
|---|---|
| 新版图像模型（`gpt-image-1` 系列、多数国产模型） | `1024x1024`、`1536x1024`、`1024x1536`、`auto` |
| DALL·E 3 | `1024x1024`、`1792x1024`、`1024x1792`（每请求只能 1 张） |
| DALL·E 2 | `256x256`、`512x512`、`1024x1024` |
| 第三方（Flux / Qwen-Image / Kolors 等） | 常见支持任意宽高比与 2K，具体看供应商文档；**不要假设 OpenAI 的尺寸表通用** |

竖版海报用 `1024x1536`，横版封面用 `1536x1024`。给了不支持的尺寸时，运气好报 400，运气不好被悄悄改成 `1024x1024`——所以生成后必须用 `save` 或 `size` 读回真实宽高（见 SKILL.md「已知坑」）。

## `/images/edits` 字段

`multipart/form-data`，不能用 JSON 提交。

| 字段 | 类型 | 说明 |
|---|---|---|
| `image` | file / file[] | 必填。png / webp / jpg，单张通常 ≤25MB；新版模型支持一次多张参考图 |
| `mask` | file | 可选。png，必须带 alpha 通道，尺寸与被编辑图一致；透明区域即重绘区域 |
| `prompt` | string | 必填。描述「改成什么」，不是「原图是什么」 |
| `model` | string | 必填 |
| `n` | int | 默认 1 |
| `size` | string | `1024x1024` / `1536x1024` / `1024x1536` / `auto` |
| `quality` | string | `low` / `medium` / `high` / `auto` |
| `input_fidelity` | string | `low` / `high`，控制对原图的保真程度；不支持时忽略 |
| `background` / `output_format` / `output_compression` | — | 同 generations |

curl 写法：

```bash
curl -sS --max-time 480 -X POST "$IMAGE_BASE_URL/images/edits" \
  -H "Authorization: Bearer $IMAGE_API_KEY" \
  -F "model=$IMAGE_MODEL" \
  -F "prompt=把背景换成纯白，保留主体和光影" \
  -F "size=1024x1024" \
  -F "image=@./input.png" \
  -F "mask=@./mask.png" \
  -o image-response.json
```

实测补充（2026-10）：

- **gpt-image 系**：`edits` 正常，`size` 精确生效（`1024x1024` 出 `1024x1024`），返回结构与 `generations` 完全一致，`usage.input_tokens_details.image_tokens` 会从 0 变成 200 左右，可以拿它确认输入图生效了。
- **qwen-image 系走第三方兼容路由**：能出图，但 **`size` 被忽略**。方图输入出 `2048x2048`，竖图输入出 `1664x2496`，比例跟输入图走。要精确尺寸只能用 gpt-image 系，或改走百炼原生协议自己指定 `size`。
- `mask` 支持度比 `size` 更差，很多兼容服务直接忽略；要「只改局部」，先用 prompt 说清区域，别指望 mask。

## 响应结构

成功：

```json
{
  "created": 1790707938,
  "data": [
    {
      "b64_json": "iVBORw0KGgo...",
      "revised_prompt": "供应商改写后的实际提示词",
      "width": 1024,
      "height": 1536
    }
  ],
  "usage": {
    "input_tokens": 42,
    "output_tokens": 4160,
    "total_tokens": 4202
  }
}
```

要点：

- `data[0]` 里 `b64_json` 与 `url` **通常只有一个**。两个都判空，别只看一个。注意 `qwen-image-3.0` 会返回 `"b64_json": ""`——**字段存在但为空字符串**。
- `width` / `height` 是**可选**扩展字段，很多服务不返回。没有就自己解码 PNG 头读尺寸。
- `revised_prompt` 只在部分模型上出现，用户不满意时把它贴给用户看，多半是模型把提示词改了。
- `usage` 同样是可选的，没有就别硬算成本。

失败：

```json
{
  "error": {
    "message": "Invalid value for 'size': 1024x1792 is not supported for this model.",
    "type": "invalid_request_error",
    "param": "size",
    "code": "invalid_size"
  }
}
```

`error.param` 是最有用的字段，直接告诉你哪个参数错了。

## 最小可用请求

```json
{
  "model": "<模型名>",
  "prompt": "<提示词>",
  "size": "1024x1536",
  "n": 1
}
```

先跑这条。跑通后再逐个加 `quality`、`background`、`output_format`、供应商私有参数。一次性堆满参数，出错时无法定位。

## qwen 兼容模式的专属字段

百炼的 qwen-image 有一套官方 OpenAI 兼容端点（`{base}/compatible-mode/v1`），请求体所有字段平铺在顶层，没有 `input` / `parameters` 嵌套。核心差异：

| 字段 | 说明 |
|---|---|
| `prompt` | 必填，推荐 ≤4500 Token |
| `image` | **图生图靠它**。公网 URL 或 `data:{MIME};base64,{data}`；单图字符串，多图字符串数组。不传 = 文生图 |
| `size` | `1024x1024`（字母 x）或 `auto`；不传由模型按提示词推荐 |
| `n` | 1–6，必须整数 |
| `negative_prompt` | 仅 3.0 系支持 |
| `prompt_extend` | 默认 `true`，会改写提示词 |
| `prompt_extend_mode` | `direct`（默认）/ `agent`；**`agent` 只给文生图，图生图传它会 400** |
| `enable_thinking` | 默认 `true`，仅在 `prompt_extend=true` 时生效，更慢但质量更高 |
| `watermark` / `seed` | 同 DashScope |

图生图**不走** `/images/edits`，也不用 multipart 和 mask。官方明确这套兼容模式不支持：异步、流式、partial image、`/images/edits`、multipart、mask。`response_format: b64_json` 会被忽略，照样返回 URL。

响应是 `data[].url` + 顶层 `usage`（`output_width` / `output_height` / `input_image_count` / `output_image_count`）。不返回 `request_id`，它在响应头 `x-request-id`。

用 OpenAI SDK 时，上面这些扩展字段要塞进 `extra_body`：

```python
resp = client.images.generate(
    model="qwen-image-3.0",
    prompt="把这张图改成水彩画风格",
    size="1024x1024",
    n=1,
    extra_body={"image": ["data:image/png;base64,..."], "prompt_extend": True},
)
```

**但第三方兼容层不一定照这个实现。** 实测有服务把 `image` 字段直接丢掉（返回 200，图与输入无关），反而支持 `/images/edits`。落地前先用一张特征明显的图跑一次，确认输出里还有原图主体。

## 非标准但常见的第三方参数

这些**不在** OpenAI 规范里，只有对应供应商支持，加了可能报 400 也可能被静默忽略：

| 参数 | 出现在 | 作用 |
|---|---|---|
| `seed` | Flux、SD 等 | 固定随机种子以复现同一张图 |
| `negative_prompt` | SD、Kolors 系 | 明确不想要的内容 |
| `steps` / `guidance_scale` | SD 系 | 采样步数与提示词贴合强度 |
| `aspect_ratio` | 部分国产模型 | 用比例代替像素尺寸，与 `size` 冲突时以供应商文档为准 |
| `watermark` / `logo_add` | 国产模型 | 是否加平台水印，商用前必须确认 |
| `reference_image` / `ref_image` | 部分模型的图生图 | 用 base64 或 URL 传参考图，字段名各家不同 |
| `callback_url` | 异步接口 | 生成完成后回调，替代轮询 |

判断方法只有一条：**看用户给的文档或一次真实响应**。没有依据就不要凭经验加。
