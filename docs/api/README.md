# 📖 MedIntel Cloud — API 文档

全栈医疗AI统一平台 API 参考。

## 架构

MedIntel Cloud 采用微服务架构，所有服务通过统一 API Gateway 暴露。

```
客户端 → API Gateway → 业务服务 → Harness 编排层 → 模型后端
```

## 服务列表

### 🏗️ 基础设施
- [OpenClaw Harness](./api/harness.md) — 统一编排框架管理

### 🔬 药物发现引擎
- MediPharma — AI 药物发现
- DrugMind — 数字分身协作
- VirtualCell — 虚拟细胞验证
- PharmaSim — 上市预测仿真

### 🏥 临床决策引擎
- MediChat-RD — 罕见病 AI 诊疗
- MedRoundtable — 科研圆桌
- MingEvidence — 临床证据
- ChroniCare — 慢病管理

### 💊 认知商业引擎
- MediSlim — 消费医疗
- CloudMemorial — AI 数字纪念
- TianYan — 商业预测
- [Minder](./api/minder.md) — 智能语音提醒

### 🧠 知识研究引擎
- DigitalSage — 100 大脑对话
- Ponder — 知识工作流
- HEOR Modeling — HEOR/HTA 建模
- BioStats — 生物统计

## 认证

所有 API 请求需要 Bearer Token:

```
Authorization: Bearer <token>
```

## 错误码

| 状态码 | 含义 |
|--------|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误 |
| 401 | 未认证 |
| 404 | 资源不存在 |
| 422 | 验证失败 |
| 500 | 服务器内部错误 |
| 503 | 服务不可用 |
