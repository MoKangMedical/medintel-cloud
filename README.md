# 🏥 MedIntel Cloud — 全栈医疗AI统一平台

> Harness（环境设计）比模型本身更重要。
> 模型可以替换，流程编排才是护城河。

## 架构概览

```
medintel-cloud/
├── core/                    # 🔧 共享核心层
│   ├── models/              #   统一数据模型 (FHIR/RWD/EHR)
│   ├── auth/                #   统一认证 & 权限
│   ├── gateway/             #   API Gateway (FastAPI)
│   └── utils/               #   通用工具
│
├── services/                # 🧩 业务服务模块
│   ├── drug_discovery/      #   🔬 药物发现引擎
│   │   ├── medi_pharma/     #     AI药物发现 (靶点→筛选→分子→ADMET)
│   │   ├── drugmind/        #     数字分身协作 (7×24 AI协作)
│   │   ├── virtual_cell/    #     虚拟细胞验证 (Benchmark)
│   │   └── pharma_sim/      #     上市预测仿真 (1801 Agent)
│   │
│   ├── clinical/            #   🏥 临床决策引擎
│   │   ├── medi_chat_rd/    #     罕见病AI诊疗 (4C体系)
│   │   ├── med_roundtable/  #     科研圆桌 (A2A架构)
│   │   ├── ming_evidence/   #     临床证据 (中国版OpenEvidence)
│   │   └── chroni_care/     #     慢病管理 (风险分层+MDT)
│   │
│   ├── cognitive_commerce/  #   💊 认知商业引擎
│   │   ├── medi_slim/       #     消费医疗 (AI体质+营销)
│   │   ├── cloud_memorial/  #     AI数字纪念 (语音克隆+人格)
│   │   ├── tianyan/         #     商业预测 (多Agent人群模拟)
│   │   └── minder/          #     智能语音提醒
│   │
│   ├── knowledge/           #   🧠 知识研究引擎
│   │   ├── digital_sage/    #     100大脑对话
│   │   ├── ponder/          #     知识工作流
│   │   ├── heor_modeling/   #     HEOR/HTA建模
│   │   └── biostats/        #     生物统计
│   │
│   └── infrastructure/      #   🏗️ 基础设施
│       └── openclaw_harness/#     统一编排框架
│
├── deploy/                  # 🚀 部署配置
│   ├── docker/
│   ├── k8s/
│   └── nginx/
│
├── docs/                    # 📖 文档
└── tests/                   # 🧪 测试
```

## 引擎说明

| 引擎 | 核心价值 | 目标客户 |
|------|---------|---------|
| 🔬 药物发现 | 靶点→候选化合物全流程 | 药企、Biotech |
| 🏥 临床决策 | 诊疗+科研+证据+管理 | 医院、科研机构 |
| 💊 认知商业 | C端消费+商业预测 | 消费医疗、品牌方 |
| 🧠 知识研究 | 知识管理+统计+建模 | 学术、咨询 |

## 快速启动

```bash
# 开发环境
docker-compose up -d

# API Gateway
cd core/gateway && uvicorn main:app --reload

# 单独服务
cd services/drug_discovery/medi_pharma && python main.py
```

## 技术栈

- **编排层:** OpenClaw-Medical-Harness (Python)
- **API:** FastAPI + OpenAPI
- **数据:** PostgreSQL + Redis + Vector DB
- **模型:** MIMO API (mimo-v2-pro/omni/flash)
- **部署:** Docker Compose → K8s

## 商业模式

- **SaaS订阅:** 按引擎模块订阅
- **用量计费:** API调用按量
- **私有化:** License费 + 部署服务
- **项目制:** 药企CRO-like合作
