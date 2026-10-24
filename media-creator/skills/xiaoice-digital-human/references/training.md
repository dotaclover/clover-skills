# 形象训练与声音训练

训练类任务耗时较长，轮询间隔建议放宽到 60 秒以上。

---

## 形象训练（三步流程）

### 1. 提交

```json
POST /openapi/customize/zero/commit
{ "vhModelType": "STUDIO", "trainingVideoUrl": "https://...", "authVideoUrl": "https://...", "voiceTemplateVersion": 1 }
```

返回 `data` 为训练任务 bizId。

### 2. 质检轮询

```
GET /openapi/customize/zero/get-ckq-result?bizId=<bizId>
```

- `data.status`：`0` 进行中（含 progress）、`1` 质检通过、`-1` 失败（看 `data.message`）。

### 3. 质检通过后启动训练

质检通过**不会自动开始训练**，必须显式调用：

```json
POST /openapi/customize/zero/start-training
{ "bizId": "<训练bizId>", "name": "我的形象", "voiceBizId": "可选，绑定已完成的声音训练" }
```

### 4. 训练结果轮询

```json
POST /openapi/customize/zero/get-training-result
{ "bizId": "<训练bizId>" }
```

- `data.status`：`0` 训练中、`1` 成功（`data.bizId` 为新形象的 bizId，用于后续视频生成）、`-1` 失败。

---

## 声音训练（两步流程）

### 1. 提交

```json
POST /openapi/customize/zero/voice/commit
{ "name": "我的声音", "trainingAudioUrl": "https://...", "languageType": "CHINESE", "audioText": "可选，录音文字" }
```

- `languageType`：`CHINESE` 或 `MULTI`；`MULTI` 可加 `"reduceNoise": 0|1`。
- 成功返回 `data` 为训练任务 bizId。

### 2. 结果轮询

```json
POST /openapi/customize/zero/voice/get-training-result
{ "bizId": "<bizId>" }
```

- `status` 同上；成功时 `data.voiceBizId` 用于形象训练绑定，**不是** `bizId`。

---

## 训练素材要求

`trainingVideoUrl` / `trainingAudioUrl` 必须是 `mediaUrl` 形式的**公网直链**（详见 `assets-and-timing.md` 的素材准备）。

- 必须是无内嵌账号密码的绝对 HTTP(S) URL，且上游可访问。
- 同一账户同类训练进行中时**不要重复提交**。
