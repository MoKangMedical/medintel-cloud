# 🏗️ OpenClaw Harness — API 文档

统一编排框架管理接口。

**Base URL:** `/harness`

## Endpoints

### `GET /health`

服务健康检查。

**Response:**
```json
{
  "status": "ok",
  "service": "OpenClaw-Harness",
  "version": "0.1.0",
  "registered_harnesses": 3
}
```

---

### `POST /register`

注册一个新的 Harness 实例。

**Request Body:**
```json
{
  "name": "diagnosis-harness-v1",
  "harness_type": "diagnosis",
  "model_provider": "mimo",
  "description": "诊断 Harness"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | ✅ | Harness 名称 (1-128字符) |
| `harness_type` | enum | ❌ | 类型: `diagnosis`, `drug_discovery`, `health_management`, `custom` |
| `model_provider` | string | ❌ | 模型后端，默认 `mimo` |
| `description` | string | ❌ | 描述 |

**Response (201):**
```json
{
  "id": "a1b2c3d4",
  "name": "diagnosis-harness-v1",
  "harness_type": "diagnosis",
  "model_provider": "mimo",
  "description": "诊断 Harness",
  "tool_count": 0,
  "status": "ready"
}
```

---

### `GET /list`

列出所有已注册的 Harness。

**Response:**
```json
{
  "harnesses": [
    {
      "id": "a1b2c3d4",
      "name": "diagnosis-harness-v1",
      "harness_type": "diagnosis",
      "model_provider": "mimo",
      "tool_count": 3,
      "status": "ready"
    }
  ],
  "total": 1
}
```

---

### `POST /execute`

执行一个已注册的 Harness。

**Request Body:**
```json
{
  "harness_id": "a1b2c3d4",
  "input_data": {
    "symptoms": ["fever", "cough", "fatigue"],
    "patient_age": 35,
    "allergies": ["penicillin"]
  }
}
```

**Response:**
```json
{
  "harness_id": "a1b2c3d4",
  "harness_name": "diagnosis-harness-v1",
  "status": "success",
  "output": { ... },
  "validation_score": 0.85,
  "execution_time_ms": 142.5,
  "metadata": {
    "domain": "diagnosis",
    "model": "mimo"
  }
}
```

**Status 值:**
- `success` — 执行成功
- `recovered` — 经过恢复后成功
- `failed` — 执行失败
- `partial` — 部分成功

---

### `POST /validate`

独立验证 Harness 输出（不经过 Harness 执行流程）。

**Request Body:**
```json
{
  "output": {
    "primary_diagnosis": "influenza",
    "differential_list": ["common_cold", "covid_19"],
    "confidence": 0.87
  },
  "domain": "diagnosis"
}
```

**Response:**
```json
{
  "passed": true,
  "score": 1.0,
  "message": "Validation passed (score: 1.00)",
  "findings": []
}
```

---

### `GET /recovery/{harness_id}`

获取指定 Harness 的失败恢复日志。

**Response:**
```json
{
  "harness_id": "a1b2c3d4",
  "escalation_events": [
    {
      "level": "high",
      "source": "validation",
      "reason": "Validation failed",
      "resolution": "degraded_gracefully",
      "context_snapshot": {
        "stage": "reasoning",
        "input_keys": ["symptoms"],
        "has_critical_items": true
      }
    }
  ],
  "total_failures": 1
}
```

## 错误响应

**404 — Harness 不存在:**
```json
{
  "detail": "Harness 'invalid_id' not found"
}
```

## 架构说明

### Harness 理论

> 模型是可替换的，Harness 才是护城河。

一个 Harness 封装了 5 个核心组件:
1. **Tool Chain** — 有序的工具执行链
2. **Information Format** — 上下文结构化与压缩
3. **Context Management** — 上下文构建与传递
4. **Failure Recovery** — 失败自动升级（重试→降级→人工）
5. **Result Validation** — 领域特定的输出验证

### 验证层级

1. **Structural** — 必要字段和类型检查
2. **Consistency** — 内部逻辑一致性
3. **Domain** — 医疗领域标准检查
4. **Safety** — 危险模式检测（如"停用所有药物"）
