# MedIntel Cloud

全栈医疗AI统一平台 — 整合诊断、治疗、随访全流程

## 一句话定义

MedIntel Cloud 不卖医疗IT系统，卖诊疗全流程的AI决策支持。从患者入院到出院随访，AI贯穿每个环节。

## 核心模块

- 智能分诊: 症状→科室→医生推荐
- 辅助诊断: 多模态数据（影像/检验/病史）→鉴别诊断
- 治疗方案: 基于循证医学的个性化方案
- 随访管理: 自动化随访提醒+效果评估
- 知识库: 临床指南/药品/检验标准

## 技术架构

- 后端: FastAPI + SQLAlchemy
- AI引擎: MIMO API + CrewAI多Agent
- 数据库: PostgreSQL + Redis
- 部署: Docker + Kubernetes

## 快速开始

    git clone https://github.com/MoKangMedical/medintel-cloud.git
    cd medintel-cloud
    docker-compose up -d

MIT License
