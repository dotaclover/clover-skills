# 可直接改的调用示例

约定：

- `$IMAGE_BASE_URL` 形如 `https://<服务地址>/v1`，**不要写死某一家**。
- `$IMAGE_API_KEY` 只从环境变量读，不进代码、不进报告。
- `$IMAGE_MODEL` 从 `GET $IMAGE_BASE_URL/models` 里挑。
- 所有示例都能在只有命令行和基础运行时的机器上跑。

```bash
export IMAGE_BASE_URL='https://<服务地址>/v1'
export IMAGE_MODEL='<模型名>'
read -rsp 'API Key: ' IMAGE_API_KEY; echo
export IMAGE_API_KEY
```

## 1. 健康检查：地址与 Key 对不对

```bash
curl -sS "$IMAGE_BASE_URL/models" \
  -H "Authorization: Bearer $IMAGE_API_KEY" \
  -o models.json -w '%{http_code}\n'
```

- `200` + 含 `data[].id` → 地址和 Key 都通。
- `404` → 路径错，多半少了 `/v1`。
- 返回 HTML → 打到了前端页，不是接口。
- `401` / `403` → Key 错，或这个 Key 没有该分组权限。

## 2. 文生图（curl，推荐加长超时）

```bash
cat > image-request.json <<'JSON'
{
  "model": "MODEL_PLACEHOLDER",
  "prompt": "A vertical poster for a coffee brand, warm morning light, minimal layout, no text, no logo",
  "size": "1024x1536",
  "n": 1
}
JSON
```

把 `MODEL_PLACEHOLDER` 换成 `$IMAGE_MODEL` 的值，然后：

```bash
curl -sS --max-time 480 -X POST "$IMAGE_BASE_URL/images/generations" \
  -H "Authorization: Bearer $IMAGE_API_KEY" \
  -H "Content-Type: application/json" \
  --data-binary "@image-request.json" \
  -o image-response.json \
  -w 'http=%{http_code} time=%{time_total}s\n'
```

超过 30 秒还在等是正常的。真要中断，先看 `image-response.json` 是否已经有内容。

## 3. 解码 b64 并保存（Python，标准库即可）

```python
import base64
import json
import pathlib
import struct


def save_images(response_path: str, prefix: str = "image") -> list[str]:
    data = json.loads(pathlib.Path(response_path).read_text(encoding="utf-8"))

    if "error" in data:
        raise RuntimeError(f"接口报错: {data['error'].get('message')}")

    saved = []
    for index, item in enumerate(data.get("data", []), start=1):
        if item.get("b64_json"):
            raw = base64.b64decode(item["b64_json"])
            ext = "png"
        elif item.get("url"):
            # URL 结果单独下载，见下一节
            print("url:", item["url"])
            continue
        else:
            raise RuntimeError("data 项里既没有 b64_json 也没有 url")

        path = pathlib.Path(f"{prefix}-{index:02d}.{ext}")
        path.write_bytes(raw)

        # PNG 头：签名 8 字节，随后 IHDR 长度 4 + 类型 4，宽高在偏移 16 与 20
        if raw[:8] == b"\x89PNG\r\n\x1a\n":
            width, height = struct.unpack(">II", raw[16:24])
            print(f"{path} {width}x{height} {len(raw)} bytes")
        saved.append(str(path))
    return saved
```

`item.get("b64_json")` 判的是**值是不是空**，不是**键在不在**——`qwen-image-3.0` 正是返回 `"b64_json": ""`，用 `if "b64_json" in item` 就会拿空串去解码然后报错。

`base64.b64decode` 默认不接受 `data:image/png;base64,` 前缀。真遇到就 `item["b64_json"].split(",", 1)[-1]`。

## 4. 下载 URL 结果并转存

```bash
curl -sS --max-time 120 "$(python -c "import json;print(json.load(open('image-response.json'))['data'][0]['url'])")" \
  -o image-01.png
file image-01.png
```

签名链接会过期，别把 URL 当成交付物，落盘之后再报路径。

## 5. 完整 Python 调用（requests）

```python
import base64
import os
import pathlib
import sys

import requests

BASE = os.environ["IMAGE_BASE_URL"]
KEY = os.environ["IMAGE_API_KEY"]
MODEL = os.environ["IMAGE_MODEL"]

payload = {
    "model": MODEL,
    "prompt": "A vertical poster for a coffee brand, warm morning light, minimal layout",
    "size": "1024x1536",
    "n": 1,
}

resp = requests.post(
    f"{BASE}/images/generations",
    headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
    json=payload,
    timeout=(10, 480),  # 连接 10 秒，读取 480 秒
)

pathlib.Path("image-response.json").write_text(resp.text, encoding="utf-8")

if resp.status_code != 200:
    sys.exit(f"HTTP {resp.status_code}: {resp.text[:500]}")

item = resp.json()["data"][0]
raw = base64.b64decode(item["b64_json"])
pathlib.Path("image-01.png").write_bytes(raw)
print("saved", len(raw), "bytes")
```

没有 `requests` 时用标准库 `urllib.request`，注意**关掉系统代理**（本机开着代理访问内网或本地服务会 502）：

```python
import json
import urllib.request

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
request = urllib.request.Request(
    f"{BASE}/images/generations",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
    method="POST",
)
with opener.open(request, timeout=480) as response:
    body = json.loads(response.read().decode("utf-8"))
```

## 6. Node.js（原生 fetch，18+）

```javascript
import { writeFileSync } from 'node:fs';

const { IMAGE_BASE_URL: base, IMAGE_API_KEY: key, IMAGE_MODEL: model } = process.env;

const res = await fetch(`${base}/images/generations`, {
  method: 'POST',
  headers: { Authorization: `Bearer ${key}`, 'Content-Type': 'application/json' },
  body: JSON.stringify({
    model,
    prompt: 'A vertical poster for a coffee brand, warm morning light, minimal layout',
    size: '1024x1536',
    n: 1,
  }),
  signal: AbortSignal.timeout(480_000),
});

const text = await res.text();
writeFileSync('image-response.json', text);
if (!res.ok) throw new Error(`HTTP ${res.status}: ${text.slice(0, 500)}`);

const item = JSON.parse(text).data[0];
writeFileSync('image-01.png', Buffer.from(item.b64_json, 'base64'));
```

`AbortSignal.timeout` 在 Node 17.3+ 才有。更老的版本用 `setTimeout` + `controller.abort()`。

## 7. OpenAI SDK

只要供应商兼容 OpenAI 协议，SDK 不用改代码，换 `base_url` 即可。

Python：

```python
import base64
import os

from openai import OpenAI

client = OpenAI(api_key=os.environ["IMAGE_API_KEY"], base_url=os.environ["IMAGE_BASE_URL"])

result = client.images.generate(
    model=os.environ["IMAGE_MODEL"],
    prompt="A vertical poster for a coffee brand, warm morning light, minimal layout",
    size="1024x1536",
    n=1,
)

item = result.data[0]
if getattr(item, "b64_json", None):
    with open("image-01.png", "wb") as fh:
        fh.write(base64.b64decode(item.b64_json))
elif getattr(item, "url", None):
    print("url:", item.url)
```

Node：

```javascript
import { writeFileSync } from 'node:fs';
import OpenAI from 'openai';

const client = new OpenAI({
  apiKey: process.env.IMAGE_API_KEY,
  baseURL: process.env.IMAGE_BASE_URL,
});

const result = await client.images.generate({
  model: process.env.IMAGE_MODEL,
  prompt: 'A vertical poster for a coffee brand, warm morning light, minimal layout',
  size: '1024x1536',
  n: 1,
});

const item = result.data[0];
if (item.b64_json) writeFileSync('image-01.png', Buffer.from(item.b64_json, 'base64'));
else console.log('url:', item.url);
```

SDK 只发它认识的字段。供应商私有参数（`seed`、`negative_prompt`、`watermark`）要么用 `extra_body`（Python）传，要么退回纯 HTTP 调：

```python
result = client.images.generate(
    model=os.environ["IMAGE_MODEL"],
    prompt="...",
    extra_body={"seed": 42, "watermark": False},
)
```

## 8. 异步任务型：提交 → 轮询 → 下载

字段名各不同，下面这套把差异集中在三个变量里，改一处就能复用：

```python
import os
import time

import requests

BASE = os.environ["IMAGE_BASE_URL"]
KEY = os.environ["IMAGE_API_KEY"]
HEADERS = {"Authorization": f"Bearer {KEY}"}

SUBMIT_PATH = "/images/generations"   # 换成供应商的提交路径
STATUS_PATH = "/tasks/{id}"           # 查询路径模板，{id} 占位
SUCCESS = {"succeeded", "success", "completed", "done"}
FAILED = {"failed", "error", "cancelled", "canceled"}

submit = requests.post(
    f"{BASE}{SUBMIT_PATH}",
    headers={**HEADERS, "Content-Type": "application/json"},
    json={"model": os.environ["IMAGE_MODEL"], "prompt": "...", "n": 1},
    timeout=(10, 60),
)
submit.raise_for_status()
task_id = (
    submit.json().get("task_id")
    or submit.json().get("id")
    or submit.json().get("request_id")
)
if not task_id:
    raise RuntimeError(f"提交响应里没有任务号: {submit.text[:300]}")

for attempt in range(120):
    time.sleep(5)
    info = requests.get(f"{BASE}{STATUS_PATH.format(id=task_id)}", headers=HEADERS, timeout=30).json()
    status = str(info.get("status", "")).lower()
    if status in SUCCESS:
        print("result:", info)   # 从 info 里找图片 URL 数组，下载后落盘
        break
    if status in FAILED:
        raise RuntimeError(f"任务失败: {info}")
else:
    print(f"仍未完成，留 task_id={task_id} 下次再查")
```

三条纪律：轮询间隔别低于 3 秒；任务号已经拿到就**不要重新提交**；超时未完成时把 `task_id` 交给用户，而不是换个模型再来一遍。

## 9. 一次跑完的落地检查

```bash
python - <<'PY'
import pathlib, struct
p = pathlib.Path("image-01.png")
raw = p.read_bytes()
assert raw[:8] == b"\x89PNG\r\n\x1a\n", "不是 PNG"
w, h = struct.unpack(">II", raw[16:24])
print(f"{p} {w}x{h} {len(raw)} bytes")
PY
```

宽高与请求不符 → 服务端改了尺寸，写进报告。0 字节或开头是 `<` → 存到了错误页，回去看原始响应。
