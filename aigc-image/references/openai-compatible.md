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
| 第三方（Flux / Seedream / Qwen-Image / Kolors 等） | 常见支持任意宽高比与 2K，具体看供应商文档；**不要假设 OpenAI 的尺寸表通用** |

竖版海报用 `1024x1536`，横版封面用 `1536x1024`。给了不支持的尺寸时，运气好报 400，运气不好被悄悄改成 `1024x1024`——所以生成后要读回真实宽高（见 `troubleshooting.md`）。

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

## 非标准但常见的第三方参数

这些**不在** OpenAI 规范里，只有对应供应商支持，加了可能报 400 也可能被静默忽略：

| 参数 | 出现在 | 作用 |
|---|---|---|
| `seed` | Flux、SD、Seedream 系 | 固定随机种子以复现同一张图 |
| `negative_prompt` | SD、Kolors 系 | 明确不想要的内容 |
| `steps` / `guidance_scale` | SD 系 | 采样步数与提示词贴合强度 |
| `aspect_ratio` | 部分国产模型 | 用比例代替像素尺寸，与 `size` 冲突时以供应商文档为准 |
| `watermark` / `logo_add` | 国产模型 | 是否加平台水印，商用前必须确认 |
| `reference_image` / `ref_image` | 部分模型的图生图 | 用 base64 或 URL 传参考图，字段名各家不同 |
| `callback_url` | 异步接口 | 生成完成后回调，替代轮询 |

判断方法只有一条：**看用户给的文档或一次真实响应**。没有依据就不要凭经验加。
