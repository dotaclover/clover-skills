# 异步图片 API（需服务方启用）

这是 Nexgate 网关的后台图片任务扩展，不能等同于上游 Images 的原生 background 模式。服务需部署相应版本并开启功能；`GET /v1/models` 无法证明它已启用。本文接口契约已与实现核对，默认公网的上线状态需服务方确认，不以付费提交探测能力。

## 提交与恢复

`POST /v1/images/tasks`，Bearer 鉴权、必填 Idempotency-Key。JSON 无 images 为文生图，带 images 为 Base64 参考图编辑（推荐）；也保留 multipart 文件编辑。都不支持 stream=true。**参考图编辑是 2026-11-04 后续源码新增能力，须部署该版本后使用；此前线上文生图实测不能证明编辑已上线。**

```bash
curl --silent --show-error --fail-with-body --connect-timeout 10 --max-time 30 \
  "$JUHE_BASE_URL/v1/images/tasks" \
  -H "Authorization: Bearer $JUHE_API_KEY" \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: order-001' \
  --data-binary @image-request.json --output image-task.json
```

环境变量示例只说明协议；已保存凭据优先使用技能 CLI，不重新索取。HTTP 202：

```json
{"task_id":"img_...","status":"pending","request_id":"..."}
```

响应 Location 为 `/v1/images/tasks/img_...`。task_id 是服务端返回值，客户端不填写；Idempotency-Key 是调用方为一次业务生成确定的稳定标识。

- key 长度 1–128，ASCII 可打印且无空格；同租户/用户/Token 内生效。
- JSON：同 key、同原始请求字节返回原任务；换 body/指定渠道返回 409，JSON 空白/顺序变化也算变化。CLI 原样发送 UTF-8 请求文件，不重新序列化。multipart 的幂等规则见下文。
- 网络中断未拿到 ID 时，保存原请求与 key，用原 Token 原样重发；不可换 key 或转同步重试。
- JSON 文生图请求上限 1 MiB；JSON 参考图和 multipart 总请求上限 64 MiB。n 为整数 1–128，上游可能进一步限制，默认示例 n=1。每用户最多 10 个排队/处理中任务。
- 202 表示任务持久化，不是预留费用或完成出图。执行时按有效权限、余额与配置处理，后续可能失败。

## JSON Base64 多参考图（推荐，需新版部署）

```json
{
  "model": "gpt-image-2",
  "prompt": "保留第一张人物，使用第二张的服装与场景",
  "size": "2048x2048",
  "n": 1,
  "images": [
    {"image_url": "data:image/png;base64,<第一张图片的完整Base64>"},
    {"image_url": "data:image/jpeg;base64,<第二张图片的完整Base64>"}
  ]
}
```

输入使用 `images[].image_url`，单张也放数组；不是 `b64_json`（它是结果字段）。可选 `mask: {"image_url":"data:image/png;base64,..."}`。只接受内联 PNG/JPEG/WebP Data URL，不接受远程 URL、file_id、裸 Base64 或字符串数组。最多 16 张参考图，每张及 mask 解码后 ≤20 MiB，JSON 总体 ≤64 MiB（包含约 4/3 膨胀的编码体积）。mask 必须 PNG。网关做 Base64/MIME 检查，最终图像有效性和上游数量限制仍由渠道决定。

把完整 JSON 以 UTF-8 保存到请求文件，使用上文 curl `--data-binary` 或 `images submit --request-file` 即可，CLI 已允许带 images 的 64 MiB 请求。同步时同一 JSON body 可发送 `/v1/images/edits`；异步改为 `/v1/images/tasks` 并提供幂等 key，查询保持不变。worker 保留 JSON 协议和图片顺序，不转成 multipart。JSON 重试仍须保持原始字节，包括空白/字段顺序。

## multipart 多参考图编辑（兼容文件上传，需新版部署）

也可和同步 `/v1/images/edits` 一样直接上传文件：

```bash
curl --silent --show-error --fail-with-body --connect-timeout 10 --max-time 120 \
  "$JUHE_BASE_URL/v1/images/tasks" \
  -H "Authorization: Bearer $JUHE_API_KEY" \
  -H 'Idempotency-Key: reference-order-001' \
  -F 'model=gpt-image-2' \
  -F 'prompt=保留第一张人物的外貌，采用第二张的服装与场景' \
  -F 'size=2048x2048' -F 'n=1' \
  -F 'image[]=@person.png' -F 'image[]=@scene.png' \
  --output image-task.json
```

让 curl 自动设置带 boundary 的 Content-Type，不手写该头。保存凭据的用户沿用技能的 credential() 或已有客户端注入鉴权，不将 Key 明文写入命令。现有 `images submit --request-file` CLI 仍只接受 JSON；multipart 使用上述 HTTP 协议，GET 可继续使用 `images get`。

- 支持重复 `image` 或重复 `image[]`，只能选一种；多图按上传顺序定义参考关系。不接受 `image[0]` 等索引字段、混用字段、图片 URL 或 base64 文本。
- 1–16 张参考图，PNG/JPEG/WebP，单文件 ≤20 MiB；可选一张 PNG `mask`，同样 ≤20 MiB。所有表单字段和文件合计 ≤64 MiB。上游可有更严格限制，16 是网关接收上限而非所有上游承诺。
- 普通字段使用小写，每字段一次；拒绝重复 model/size/n/stream 等，stream 只能省略或 false。size 沿用固定价短边 1K/2K/4K 的 1/2/4 倍规则。
- multipart 重试使用原 Token、同一 key、相同字段值、相同图片字节与顺序及 mask。boundary、文件名、普通字段排列变化不改变任务；参考图顺序或内容变化返回 409。拿到 task_id 后只 GET。
- 服务器持久保存规范化 multipart 二进制，worker 调用原 edits 链路，上游仍接收 multipart 文件。Redis 只放任务 ID。终态清除上传 payload。
- 202 在上传完成并持久化后返回，不包含上游生成等待时间，但上传大图耗时不能省略。

## 查询与结果

```bash
python /path/to/juhe-nexgate/scripts/juhe.py images get --id img_... --output image-result.json
```

在技能外的工作目录执行，将 /path/to 替换为脚本安装路径。对应 `GET /v1/images/tasks/{task_id}`，原服务地址和提交时同一 Token。不同 Token/用户/租户查询为 404。耗尽/过期 Token 可查询已有结果，主动禁用或删除的 Token 不可用；不在查询前调用 models。

自定义服务地址放在子命令前：`python /path/to/juhe-nexgate/scripts/juhe.py images --base-url https://your-trusted-host.example get --id img_... --output image-result.json`。只使用用户授权的可信 HTTPS 服务。

```json
{
  "task_id":"img_...","status":"completed","request_id":"...",
  "created_at":1793664000,"updated_at":1793664030,"http_status":200,
  "result":{"data":[{"b64_json":"..."}]}
}
```

| status | 行为 |
| --- | --- |
| pending / processing | 每 2–5 秒查同一 ID，设置客户端总等待期限 |
| completed | 读取 result.data[] 的 b64_json 或 url，保存结果 |
| failed | 停止轮询，检查 error / result 中的错误，修复后是否新建由用户决定 |
| needs_review | 停止自动重提，保留 request_id/task_id，请服务方核查生成及账务 |

GET 的 HTTP 200 只表示查询成功。http_status 是内部图片请求状态，仍须判断任务 status。客户端等待期限到达不取消服务端任务，稍后可继续 GET。未知状态保留响应并报告，不猜测完成。

CLI get 将完整 JSON 写到 --output，stdout 只含状态、ID、结果数量和文件路径，避免大量 base64 输出；退出码 0 表示请求成功，不保证任务 completed。保存首张 base64 示例：

```python
import base64, json
from pathlib import Path
task = json.loads(Path("image-result.json").read_text(encoding="utf-8"))
if task["status"] != "completed":
    raise SystemExit("任务尚未成功；保留任务 ID 查询或排错")
item = task["result"]["data"][0]
if item.get("b64_json"):
    Path("image.png").write_bytes(base64.b64decode(item["b64_json"], validate=True))
else:
    raise SystemExit("结果为 URL；按 images.md 下载原结果，不附带 API Key")
```

扩展结果上限 64 MiB，超限可能 needs_review；URL 仍遵从上游有效期。无取消接口，不自动回放执行中任务，不承诺中断时未扣费或已自动退款。

## 接入错误

- 400：参数、key、stream 或数量错误。
- 401/403：凭据、身份、租户/权限拒绝；先检查配置来源。
- 提交 404：路径或部署版本不匹配；查询 404：也可能原 Token/租户不匹配。
- 409：同幂等 key 请求不同，恢复原请求；不要为绕过冲突随意生成新 key。
- 429：频率/活跃任务上限或余额，按错误区分；已有任务继续查询。
- 503：异步未启用或 Redis 配置不可用，联系服务方；不自动转同步创建。
- 网络/5xx：提交结果可能未知，按同 key 原始请求恢复；GET 可稍后重查。
