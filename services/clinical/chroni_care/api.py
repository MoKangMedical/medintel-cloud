"""
ChroniCare 慢病管理 — 整合版
源自 chronicdiseasemanagement 项目，适配 MedIntel Cloud monorepo
核心能力：风险分层、干预推荐、MDT多学科协作
"""

from fastapi import Depends, APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from enum import Enum
from datetime import datetime, date

from core.utils.mimo_client import get_mimo_client, MIMOClient
from core.models.patient import Patient

router = APIRouter()


class RiskLevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class ChronicDisease(str, Enum):
    DIABETES = "diabetes"              # 糖尿病
    HYPERTENSION = "hypertension"       # 高血压
    CKD = "ckd"                         # 慢性肾病
    COPD = "copd"                       # 慢阻肺
    HEART_FAILURE = "heart_failure"     # 心力衰竭
    STROKE = "stroke"                   # 脑卒中
    CANCER = "cancer"                   # 恶性肿瘤


class RiskAssessmentRequest(BaseModel):
    patient_id: str
    disease_type: ChronicDisease
    lab_results: Optional[Dict[str, float]] = None
    vital_signs: Optional[Dict[str, float]] = None
    lifestyle: Optional[Dict[str, str]] = None
    medication_adherence: Optional[float] = Field(None, ge=0, le=1)


class RiskAssessmentResponse(BaseModel):
    patient_id: str
    disease_type: str
    risk_level: RiskLevel
    risk_score: float = Field(..., ge=0, le=1)
    risk_factors: List[str] = []
    protective_factors: List[str] = []
    recommendations: List[str] = []
    next_assessment_date: Optional[date] = None


class InterventionPlan(BaseModel):
    id: str
    patient_id: str
    disease_type: str
    interventions: List[Dict[str, str]] = []
    goals: List[str] = []
    timeline: str = ""
    responsible_team: List[str] = []


class MDTRequest(BaseModel):
    patient_id: str
    disease_type: ChronicDisease
    clinical_question: str
    specialists: List[str] = Field(
        default=["内分泌科", "心内科", "肾内科", "营养科", "康复科"],
        description="参与MDT的科室",
    )


class MDTResponse(BaseModel):
    session_id: str
    patient_id: str
    specialist_opinions: Dict[str, str] = {}
    consensus: str = ""
    action_plan: List[str] = []


class DistrictDashboard(BaseModel):
    district: str
    total_patients: int
    risk_distribution: Dict[str, int] = {}
    control_rate: Dict[str, float] = {}
    alerts: List[str] = []


@router.get("/health")
async def health():
    return {"status": "ok", "service": "ChroniCare", "version": "2.0.0",
            "features": ["风险分层", "干预推荐", "MDT协作", "区域看板"]}


@router.post("/risk-assessment", response_model=RiskAssessmentResponse)
async def assess_risk(
    request: RiskAssessmentRequest,
    mimo: MIMOClient = Depends(get_mimo_client),
):
    """慢病风险分层评估"""
    context_parts = [
        f"患者ID: {request.patient_id}",
        f"慢病类型: {request.disease_type.value}",
    ]
    if request.lab_results:
        context_parts.append(f"检验结果: {request.lab_results}")
    if request.vital_signs:
        context_parts.append(f"生命体征: {request.vital_signs}")
    if request.lifestyle:
        context_parts.append(f"生活方式: {request.lifestyle}")
    if request.medication_adherence is not None:
        context_parts.append(f"用药依从性: {request.medication_adherence:.0%}")

    prompt = f"""请对以下慢病患者进行风险分层评估：

{chr(10).join(context_parts)}

请评估：
1. 整体风险等级 (low/moderate/high/critical)
2. 风险评分 (0-1)
3. 主要风险因素
4. 保护因素
5. 干预建议
6. 下次评估时间"""

    try:
        analysis = await mimo.chat([
            {"role": "system", "content": f"你是{request.disease_type.value}慢病管理专家。"},
            {"role": "user", "content": prompt},
        ])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return RiskAssessmentResponse(
        patient_id=request.patient_id,
        disease_type=request.disease_type.value,
        risk_level=RiskLevel.MODERATE,
        risk_score=0.5,
        recommendations=[analysis],
    )


@router.post("/intervention-plan")
async def create_intervention_plan(
    request: RiskAssessmentRequest,
    mimo: MIMOClient = Depends(get_mimo_client),
):
    """生成个性化干预方案"""
    prompt = f"""为{request.disease_type.value}患者制定个性化干预方案。

患者信息：
- ID: {request.patient_id}
- 检验结果: {request.lab_results or '无'}
- 生命体征: {request.vital_signs or '无'}
- 生活方式: {request.lifestyle or '无'}
- 用药依从性: {request.medication_adherence or '未知'}

请制定包括药物、饮食、运动、监测、随访的综合方案。"""

    try:
        plan_text = await mimo.chat([
            {"role": "system", "content": "你是慢病管理专家，制定个性化干预方案。"},
            {"role": "user", "content": prompt},
        ])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "patient_id": request.patient_id,
        "plan": plan_text,
        "created_at": datetime.now().isoformat(),
    }


@router.post("/mdt", response_model=MDTResponse)
async def mdt_consultation(
    request: MDTRequest,
    mimo: MIMOClient = Depends(get_mimo_client),
):
    """MDT多学科协作"""
    specialist_opinions = {}
    session_id = f"mdt-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    for specialist in request.specialists:
        prompt = f"""作为{specialist}专家，请对以下慢病患者提出专业意见：

患者ID: {request.patient_id}
慢病类型: {request.disease_type.value}
临床问题: {request.clinical_question}

请从你的专业角度给出诊疗建议。"""

        try:
            opinion = await mimo.chat([
                {"role": "system", "content": f"你是{specialist}专家。"},
                {"role": "user", "content": prompt},
            ])
            specialist_opinions[specialist] = opinion
        except Exception:
            specialist_opinions[specialist] = f"[{specialist}] 暂无意见"

    # 综合意见
    all_opinions = "\n".join(f"【{k}】{v[:200]}" for k, v in specialist_opinions.items())
    try:
        consensus = await mimo.chat([
            {"role": "system", "content": "你是MDT协调人，请综合各专家意见形成共识。"},
            {"role": "user", "content": f"各科室意见:\n{all_opinions}"}],
        )
    except Exception:
        consensus = "MDT讨论完成，请查看各科室意见。"

    return MDTResponse(
        session_id=session_id,
        patient_id=request.patient_id,
        specialist_opinions=specialist_opinions,
        consensus=consensus,
    )


@router.get("/dashboard/{district}")
async def district_dashboard(district: str):
    """区域慢病管理看板"""
    # TODO: 接入实际数据
    return DistrictDashboard(
        district=district,
        total_patients=0,
        risk_distribution={},
        control_rate={},
        alerts=[],
    )
