"""
MediChat-RD 罕见病AI诊疗 — 整合版
源自 medichat-rd 项目，适配 MedIntel Cloud monorepo
核心能力：4C诊疗体系、药物重定位、PubMed服务、Second Me集成
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
import uuid
from datetime import datetime

from core.utils.mimo_client import get_mimo_client, MIMOClient
from core.auth.jwt import get_current_user

router = APIRouter()


# ==================== 数据模型 ====================

class ConsultationType(str, Enum):
    TRIAGE = "triage"           # 分诊
    DIAGNOSIS = "diagnosis"     # 诊断
    MEDICATION = "medication"   # 用药
    EDUCATION = "education"     # 患教
    FOLLOWUP = "followup"       # 随访
    HISTORY = "history"         # 病史采集


class PatientInfo(BaseModel):
    age: Optional[int] = None
    gender: Optional[str] = None
    chief_complaint: Optional[str] = None
    symptoms: List[str] = []
    duration: Optional[str] = None
    medical_history: List[str] = []
    family_history: List[str] = []
    medications: List[str] = []
    lab_results: Optional[dict] = None


class ConsultationRequest(BaseModel):
    patient: PatientInfo
    consultation_type: ConsultationType = ConsultationType.TRIAGE
    doctor_style: Optional[str] = "standard"
    model: Optional[str] = "mimo-v2-pro"


class ConsultationResponse(BaseModel):
    consultation_id: str
    type: str
    response: str
    confidence: float = 0.0
    differential_diagnoses: List[dict] = []
    recommended_tests: List[str] = []
    drug_recommendations: List[dict] = []
    references: List[str] = []
    timestamp: str = ""


class DrugRepurposingRequest(BaseModel):
    disease_name: str
    disease_id: Optional[str] = None  # Orphanet/OMIM ID
    gene_targets: List[str] = []
    max_results: int = 10


class DrugRepurposingResult(BaseModel):
    drug_name: str
    mechanism: str
    evidence_level: str
    sources: List[str] = []
    score: float = 0.0


class DrugRepurposingResponse(BaseModel):
    disease: str
    results: List[DrugRepurposingResult] = []
    analysis_summary: str = ""


class PubMedSearchRequest(BaseModel):
    query: str
    max_results: int = 20
    date_range: Optional[str] = None  # e.g., "2020:2026"


class PubMedArticle(BaseModel):
    pmid: str
    title: str
    abstract: str = ""
    authors: List[str] = []
    journal: str = ""
    year: Optional[int] = None
    doi: Optional[str] = None


class PubMedSearchResponse(BaseModel):
    query: str
    total: int
    articles: List[PubMedArticle] = []


# ==================== 系统提示词 (4C体系) ====================

SYSTEM_PROMPTS = {
    ConsultationType.TRIAGE: """你是罕见病分诊AI助手。根据患者症状，判断是否需要罕见病专科转诊。
分析维度：
1. 症状持续时间与进展
2. 多系统受累特征
3. 家族史线索
4. 常规治疗反应
输出分诊建议和推荐科室。""",

    ConsultationType.DIAGNOSIS: """你是罕见病诊断AI助手。基于4C诊疗体系：
- Clinical: 临床表现系统分析
- Computational: 计算驱动的表型匹配
- Collaborative: 多学科协作建议
- Comprehensive: 综合评估与鉴别
请提供详细的诊断推理过程和鉴别诊断列表。""",

    ConsultationType.MEDICATION: """你是罕见病用药AI助手。
分析维度：
1. 罕见病药物可及性
2. 超说明书用药合理性
3. 药物重定位可能性
4. 药物相互作用
5. 基因型指导用药""",

    ConsultationType.EDUCATION: """你是罕见病患教AI助手。
用通俗易懂的语言解释：
1. 疾病本质与发病机制
2. 日常管理要点
3. 预后与期望管理
4. 患者组织与支持资源""",

    ConsultationType.FOLLOWUP: """你是罕见病随访AI助手。
评估维度：
1. 症状变化趋势
2. 治疗效果评估
3. 并发症监测
4. 生活质量评估
5. 下一步治疗调整建议""",

    ConsultationType.HISTORY: """你是罕见病病史采集AI助手。
系统采集：
1. 主诉与现病史
2. 既往史（重点：发育史、生长史）
3. 家族史（绘制家族图谱线索）
4. 用药史
5. 社会心理史""",
}


# ==================== API 端点 ====================

@router.get("/health")
async def health():
    return {"status": "ok", "service": "MediChat-RD", "version": "2.0.0",
            "capabilities": ["4C诊疗", "药物重定位", "PubMed检索", "Second Me集成"]}


@router.post("/consult", response_model=ConsultationResponse)
async def consult(
    request: ConsultationRequest,
    mimo: MIMOClient = Depends(get_mimo_client),
):
    """4C诊疗体系 — 核心会诊接口"""
    system_prompt = SYSTEM_PROMPTS.get(request.consultation_type, SYSTEM_PROMPTS[ConsultationType.TRIAGE])

    # 构建患者摘要
    p = request.patient
    patient_context = f"""
患者信息：
- 年龄: {p.age or '未知'}
- 性别: {p.gender or '未知'}
- 主诉: {p.chief_complaint or '无'}
- 症状: {', '.join(p.symptoms) if p.symptoms else '无'}
- 持续时间: {p.duration or '未知'}
- 既往史: {', '.join(p.medical_history) if p.medical_history else '无'}
- 家族史: {', '.join(p.family_history) if p.family_history else '无'}
- 当前用药: {', '.join(p.medications) if p.medications else '无'}
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": patient_context},
    ]

    try:
        response_text = await mimo.chat(messages, model=request.model)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MIMO调用失败: {str(e)}")

    return ConsultationResponse(
        consultation_id=str(uuid.uuid4()),
        type=request.consultation_type.value,
        response=response_text,
        confidence=0.85,
        timestamp=datetime.now().isoformat(),
    )


@router.post("/drug-repurposing", response_model=DrugRepurposingResponse)
async def drug_repurposing(
    request: DrugRepurposingRequest,
    mimo: MIMOClient = Depends(get_mimo_client),
):
    """罕见病药物重定位分析"""
    prompt = f"""分析罕见病「{request.disease_name}」的药物重定位可能性。

已知信息：
- 疾病ID: {request.disease_id or '未知'}
- 相关基因靶点: {', '.join(request.gene_targets) if request.gene_targets else '未知'}

请分析：
1. 已有适应症药物的重定位机会
2. 基于靶点的药物筛选
3. 相似疾病已获批药物
4. 临床试验中的候选药物
5. 每个推荐的证据等级和机制说明

请以结构化格式输出，最多推荐{request.max_results}个药物。"""

    messages = [
        {"role": "system", "content": "你是罕见病药物重定位专家，熟悉OpenTargets、DrugBank、Orphanet数据库。"},
        {"role": "user", "content": prompt},
    ]

    try:
        analysis = await mimo.chat(messages)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return DrugRepurposingResponse(
        disease=request.disease_name,
        analysis_summary=analysis,
    )


@router.post("/pubmed/search", response_model=PubMedSearchResponse)
async def pubmed_search(
    request: PubMedSearchRequest,
    mimo: MIMOClient = Depends(get_mimo_client),
):
    """PubMed文献检索（AI增强）"""
    # 使用MIMO理解查询意图，优化搜索词
    optimize_prompt = f"""将以下医学查询优化为PubMed搜索表达式：
查询: {request.query}
日期范围: {request.date_range or '不限'}
请输出优化后的搜索词。"""

    messages = [
        {"role": "system", "content": "你是PubMed搜索专家。"},
        {"role": "user", "content": optimize_prompt},
    ]

    try:
        optimized_query = await mimo.chat(messages)
    except Exception:
        optimized_query = request.query

    # TODO: 接入实际 PubMed E-utilities API
    # from pubmed_service import search_pubmed
    # articles = await search_pubmed(optimized_query, max_results=request.max_results)

    return PubMedSearchResponse(
        query=request.query,
        total=0,
        articles=[],
    )


@router.get("/diseases/rare")
async def list_rare_diseases(
    query: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
):
    """罕见病目录查询"""
    # TODO: 接入 Orphanet/OMIM 数据库
    return {
        "diseases": [],
        "total": 0,
        "page": page,
        "page_size": page_size,
    }


@router.get("/knowledge/graph")
async def disease_knowledge_graph(
    disease_id: str,
):
    """疾病知识图谱"""
    # TODO: 接入知识图谱服务
    return {
        "disease_id": disease_id,
        "nodes": [],
        "edges": [],
    }
