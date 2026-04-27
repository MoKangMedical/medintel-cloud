# 🍐 念念 (Minder) — API 文档

你的第二记忆，珍藏每一个念想。
基于AI的智能语音提醒服务。

**Base URL:** `/api/minder`

## Endpoints

### `GET /health`

服务健康检查。

**Response:**
```json
{
  "status": "ok",
  "service": "Minder",
  "version": "0.1.0"
}
```

---

### `POST /reminders`

创建一个新的念想。

**Request Body:**
```json
{
  "content": "明天下午3点去医院复查",
  "voice_input": true,
  "category": "健康",
  "remind_at": "2024-04-15T15:00:00",
  "location": "协和医院"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `content` | string | ✅ | 念想内容（自然语言） |
| `voice_input` | bool | ❌ | 是否语音输入，默认 false |
| `category` | string | ❌ | 分类 |
| `remind_at` | string | ❌ | 提醒时间 (ISO 8601) |
| `location` | string | ❌ | 地点提示 |

**Response (201):**
```json
{
  "id": "minder_000001",
  "content": "明天下午3点去医院复查",
  "category": "健康",
  "remind_at": "2024-04-15T15:00:00",
  "location": "协和医院",
  "status": "pending",
  "created_at": "2024-04-14T12:00:00",
  "encouragement": "你真棒！继续加油 💪"
}
```

---

### `GET /reminders`

列出所有念想。

**Query Parameters:**
| 参数 | 类型 | 说明 |
|------|------|------|
| `status` | string | 过滤状态: `pending`, `completed` |

**Response:**
```json
{
  "reminders": [ ... ],
  "total": 5
}
```

---

### `GET /reminders/{id}`

获取单个念想。

**Response:** 单个 Reminder 对象。

---

### `PUT /reminders/{id}/complete`

完成念想 ✅

**Response:** 更新后的 Reminder 对象，status 变为 `completed`。

---

### `DELETE /reminders/{id}`

删除念想。

**Response:**
```json
{
  "deleted": true
}
```

---

### `POST /nlp/process`

AI 自然语言处理 — 提取时间、地点、分类。

**Request Body:**
```json
{
  "text": "明天下午3点去协和医院复查，记得带上之前的检查报告"
}
```

**Response:**
```json
{
  "extracted_time": "tomorrow",
  "extracted_category": "健康",
  "extracted_location": null,
  "cleaned_content": "去协和医院复查，记得带上之前的检查报告",
  "confidence": 0.75
}
```

## 念想状态

| 状态 | 说明 |
|------|------|
| `pending` | 待完成 |
| `completed` | 已完成 |

## 设计理念

- 🎤 **语音优先** — 支持语音输入，说出念想即可
- 🤖 **AI 理解** — 自动提取时间、地点、分类
- 💾 **本地存储** — 数据安全保存在本地
- 📱 **PWA 支持** — 可添加到手机主屏幕
- 💝 **念想卡片** — 完成后获得鼓励语
