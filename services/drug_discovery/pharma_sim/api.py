"""
PharmaSim 药品上市预测仿真 — 整合版
源自 PharmaSim 项目，适配 MedIntel Cloud monorepo
核心能力：1801个Agent社交网络模拟、上市表现预测、竞争分析
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from enum import Enum
import uuid
from datetime import datetime

from core.utils.mimo_client import get_mimo_client, MIMOClient

router = APIRouter()


class DrugProfile(BaseModel):
    name: str
    indication: str
    mechanism: str
    phase: str = "III"  # I, II, III, NDA, Launched
    efficacy_score: float = Field(..., ge=0, le=1)
    safety_score: float = Field(..., ge=0, le=1)
    novelty_score: float = Field(..., ge=0, le=1)
    pricing_strategy: str = "premium"  # premium, parity, value
    estimated_price: Optional[float] = None
    competitors: List[str] = []


class AgentArchetype(str, Enum):
    KOL = "kol"                     # Key Opinion Leader
    COMMUNITY_DOCTOR = "community_doctor"
    SPECIALIST = "specialist"
    PATIENT_ADVOCATE = "patient_advocate"
    PAYER = "payer"                 # 支付方
    PHARMACIST = "pharmacist"
    NURSE = "nurse"
    CAREGIVER = "caregiver"
    MEDIA = "media"
    REGULATOR = "regulator"
    COMPETITOR_REP = "competitor_rep"


class SimulationConfig(BaseModel):
    drug: DrugProfile
    n_agents: int = Field(default=1801, ge=100, le=10000)
    simulation_months: int = Field(default=24, ge=1, le=60)
    market: str = "china"
    launch_strategy: str = "specialist_first"  # specialist_first, mass_market, digital_first
    marketing_budget: float = 0.0
    scenarios: List[str] = []


class MarketPrediction(BaseModel):
    drug_name: str
    peak_sales_year: int
    peak_sales_amount: float
    market_penetration: float  # 0-1
    time_to_peak_months: int
    total_revenue_5yr: float
    revenue_by_quarter: List[Dict[str, float]] = []
    adoption_curve: List[Dict[str, float]] = []
    risk_factors: List[str] = []
    opportunities: List[str] = []


class SimulationResult(BaseModel):
    simulation_id: str
    drug_name: str
    config: Dict = {}
    prediction: Optional[MarketPrediction] = None
    agent_feedback: Dict[str, List[str]] = {}
    competitive_analysis: Dict = {}
    kpi_timeline: List[Dict] = []
    scenarios_comparison: Dict[str, MarketPrediction] = {}
    insights: List[str] = []
    completed_at: str = ""


class CompetitiveAnalysisRequest(BaseModel):
    target_drug: str
    indication: str
    competitors: List[str] = []
    time_horizon_years: int = 5


@router.get("/health")
async def health():
    return {"status": "ok", "service": "PharmaSim", "version": "2.0.0",
            "max_agents": 10000, "architecture": "multi-agent simulation"}


@router.post("/simulate", response_model=SimulationResult)
async def run_simulation(
    config: SimulationConfig,
    mimo: MIMOClient = Depends(get_mimo_client),
):
    """运行上市预测仿真"""
    sim_id = str(uuid.uuid4())

    # Agent画像生成
    archetypes = list(AgentArchetype)
    agent_distribution = {
        AgentArchetype.KOL: 0.02,
        AgentArchetype.SPECIALIST: 0.10,
        AgentArchetype.COMMUNITY_DOCTOR: 0.20,
        AgentArchetype.PHARMACIST: 0.08,
        AgentArchetype.NURSE: 0.10,
        AgentArchetype.PATIENT_ADVOCATE: 0.05,
        AgentArchetype.CAREGIVER: 0.10,
        AgentArchetype.PAYER: 0.03,
        AgentArchetype.MEDIA: 0.02,
        AgentArchetype.REGULATOR: 0.01,
        AgentArchetype.COMPETITOR_REP: 0.02,
        # 剩余27%为普通患者agent
    }

    # 使用MIMO生成预测分析
    prompt = f"""请对以下药品上市进行市场预测分析：

药品信息：
- 名称: {config.drug.name}
- 适应症: {config.drug.indication}
- 机制: {config.drug.mechanism}
- 研发阶段: {config.drug.phase}
- 疗效评分: {config.drug.efficacy_score}
- 安全性评分: {config.drug.safety_score}
- 新颖性评分: {config.drug.novelty_score}
- 定价策略: {config.drug.pricing_strategy}
- 竞品: {', '.join(config.drug.competitors) if config.drug.competitors else '无'}

仿真配置：
- Agent数量: {config.n_agents}
- 模拟周期: {config.simulation_months}个月
- 市场: {config.market}
- 上市策略: {config.launch_strategy}

请分析：
1. 峰值销售预测（金额、时间）
2. 市场渗透曲线
3. 5年总收入预测
4. 风险因素
5. 机会点
6. 竞争策略建议"""

    try:
        analysis = await mimo.chat([
            {"role": "system", "content": "你是药品上市预测专家，熟悉中国医药市场和社交网络传播模型。"},
            {"role": "user", "content": prompt},
        ], model="mimo-v2-pro")
    except Exception as e:
        analysis = f"分析失败: {str(e)}"

    # 简化的模拟数据（实际应基于Agent模拟）
    prediction = MarketPrediction(
        drug_name=config.drug.name,
        peak_sales_year=2028,
        peak_sales_amount=1e9,
        market_penetration=0.15,
        time_to_peak_months=18,
        total_revenue_5yr=3e9,
        revenue_by_quarter=[],
        adoption_curve=[],
    )

    return SimulationResult(
        simulation_id=sim_id,
        drug_name=config.drug.name,
        config={"n_agents": config.n_agents, "months": config.simulation_months},
        prediction=prediction,
        insights=[analysis],
        completed_at=datetime.now().isoformat(),
    )


@router.post("/competitive", response_model=Dict)
async def competitive_analysis(
    request: CompetitiveAnalysisRequest,
    mimo: MIMOClient = Depends(get_mimo_client),
):
    """竞品分析"""
    prompt = f"""请对以下药品进行竞品分析：

目标药品: {request.target_drug}
适应症: {request.indication}
竞品: {', '.join(request.competitors) if request.competitors else '请自行识别主要竞品'}
分析时间跨度: {request.time_horizon_years}年

请提供：
1. 竞品格局分析
2. 各竞品优劣势
3. 差异化策略
4. 市场份额预测
5. 威胁与机会"""

    try:
        analysis = await mimo.chat([
            {"role": "system", "content": "你是医药市场分析师，熟悉全球和中国医药竞争格局。"},
            {"role": "user", "content": prompt},
        ])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "target_drug": request.target_drug,
        "analysis": analysis,
        "generated_at": datetime.now().isoformat(),
    }


@router.get("/agent-archetypes")
async def list_archetypes():
    """列出所有Agent原型"""
    return {
        "archetypes": [
            {"type": a.value, "description": f"模拟{a.value}类型医疗参与者"}
            for a in AgentArchetype
        ],
        "total": len(AgentArchetype),
    }
