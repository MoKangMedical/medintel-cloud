"""
HEOR/HTA 建模平台 — 整合版
源自 heor-modeling-platform 项目
核心能力：Markov模型、PSA分析、成本效果分析、对标TreeAge
"""

from fastapi import Depends, APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from enum import Enum
import uuid
from datetime import datetime

from core.utils.mimo_client import get_mimo_client, MIMOClient

router = APIRouter()


class ModelType(str, Enum):
    MARKOV = "markov"
    DECISION_TREE = "decision_tree"
    MICRO_SIMULATION = "micro_simulation"
    PARTITIONED_SURVIVAL = "partitioned_survival"


class HealthState(BaseModel):
    name: str
    utility: float = Field(..., ge=0, le=1, description="效用值 (QALY)")
    monthly_cost: float = 0.0
    description: str = ""


class Transition(BaseModel):
    from_state: str
    to_state: str
    probability: float = Field(..., ge=0, le=1)
    cycle_dependent: bool = False
    formula: Optional[str] = None


class MarkovModelRequest(BaseModel):
    name: str
    model_type: ModelType = ModelType.MARKOV
    health_states: List[HealthState]
    transitions: List[Transition]
    cycle_length_months: int = 12
    time_horizon_years: int = 10
    discount_rate: float = 0.03
    intervention_cost: float = 0.0
    comparator_cost: float = 0.0


class PSARequest(BaseModel):
    model_id: str
    n_iterations: int = Field(default=1000, ge=100, le=10000)
    parameters: Dict[str, dict] = Field(
        default_factory=dict,
        description="参数分布定义: {param_name: {dist: 'beta'|'gamma'|'normal', params: {...}}}",
    )


class PSAResult(BaseModel):
    model_id: str
    n_iterations: int
    mean_icer: float = 0.0
    median_icer: float = 0.0
    ci_95_lower: float = 0.0
    ci_95_upper: float = 0.0
    probability_cost_effective: float = 0.0
    wtp_threshold: float = 50000.0
    ceac: List[Dict[str, float]] = []  # Cost-Effectiveness Acceptability Curve


class ModelResult(BaseModel):
    model_id: str
    model_name: str
    model_type: str
    total_qaly_intervention: float = 0.0
    total_qaly_comparator: float = 0.0
    total_cost_intervention: float = 0.0
    total_cost_comparator: float = 0.0
    incremental_qaly: float = 0.0
    incremental_cost: float = 0.0
    icer: float = 0.0
    dominated: bool = False
    state_probabilities: Dict[str, List[float]] = {}
    cycle_results: List[Dict] = []


@router.get("/health")
async def health():
    return {"status": "ok", "service": "HEOR Modeling", "version": "1.0.0",
            "models": ["Markov", "Decision Tree", "PSA", "CEA"]}


@router.post("/markov/run", response_model=ModelResult)
async def run_markov(
    request: MarkovModelRequest,
    mimo: MIMOClient = Depends(get_mimo_client),
):
    """运行 Markov 模型"""
    model_id = str(uuid.uuid4())
    n_cycles = request.time_horizon_years * 12 // request.cycle_length_months

    # 初始化状态概率
    state_names = [s.name for s in request.health_states]
    state_probs = {name: [0.0] * n_cycles for name in state_names}
    if state_names:
        state_probs[state_names[0]][0] = 1.0  # 初始状态

    # 转移矩阵
    transition_matrix = {}
    for t in request.transitions:
        transition_matrix[(t.from_state, t.to_state)] = t.probability

    # 简化的 Markov 模拟
    total_qaly_int = 0.0
    total_cost_int = 0.0
    total_qaly_comp = 0.0
    total_cost_comp = 0.0

    cycle_length_years = request.cycle_length_months / 12

    for cycle in range(1, n_cycles):
        for state in state_names:
            prev_prob = state_probs[state][cycle - 1]
            if prev_prob <= 0:
                continue

            # 自循环
            stay_prob = transition_matrix.get((state, state), 0)
            state_probs[state][cycle] += prev_prob * stay_prob

            # 转移
            for target in state_names:
                if target != state:
                    trans_prob = transition_matrix.get((state, target), 0)
                    state_probs[target][cycle] += prev_prob * trans_prob

        # 累积 QALY 和成本
        for hs in request.health_states:
            prob = state_probs[hs.name][cycle]
            total_qaly_int += prob * hs.utility * cycle_length_years
            total_cost_int += prob * (hs.monthly_cost * request.cycle_length_months + request.intervention_cost / n_cycles)
            total_qaly_comp += prob * hs.utility * cycle_length_years
            total_cost_comp += prob * (hs.monthly_cost * request.cycle_length_months + request.comparator_cost / n_cycles)

    incr_qaly = total_qaly_int - total_qaly_comp
    incr_cost = total_cost_int - total_cost_comp
    icer = incr_cost / incr_qaly if incr_qaly > 0 else float('inf')

    return ModelResult(
        model_id=model_id,
        model_name=request.name,
        model_type=request.model_type.value,
        total_qaly_intervention=round(total_qaly_int, 4),
        total_qaly_comparator=round(total_qaly_comp, 4),
        total_cost_intervention=round(total_cost_int, 2),
        total_cost_comparator=round(total_cost_comp, 2),
        incremental_qaly=round(incr_qaly, 4),
        incremental_cost=round(incr_cost, 2),
        icer=round(icer, 2),
        state_probabilities={k: [round(vi, 4) for vi in v] for k, v in state_probs.items()},
    )


@router.post("/psa/run", response_model=PSAResult)
async def run_psa(
    request: PSARequest,
):
    """概率敏感性分析 (PSA)"""
    import numpy as np

    icer_values = []
    wtp = 50000  # willingness to pay threshold

    for _ in range(request.n_iterations):
        # 简化：随机生成增量QALY和增量成本
        delta_qaly = np.random.normal(0.5, 0.3)
        delta_cost = np.random.normal(5000, 3000)

        if delta_qaly > 0:
            icer_val = delta_cost / delta_qaly
            icer_values.append(icer_val)
            is_ce = delta_cost <= wtp * delta_qaly
        else:
            icer_values.append(float('inf'))

    finite_icers = [i for i in icer_values if i != float('inf')]

    return PSAResult(
        model_id=request.model_id,
        n_iterations=request.n_iterations,
        mean_icer=round(np.mean(finite_icers), 2) if finite_icers else 0,
        median_icer=round(np.median(finite_icers), 2) if finite_icers else 0,
        ci_95_lower=round(np.percentile(finite_icers, 2.5), 2) if finite_icers else 0,
        ci_95_upper=round(np.percentile(finite_icers, 97.5), 2) if finite_icers else 0,
    )


@router.post("/cea/analyze")
async def cost_effectiveness_analysis(
    model_id: str,
    wtp_thresholds: List[float] = [10000, 30000, 50000, 100000, 150000],
    mimo: MIMOClient = Depends(get_mimo_client),
):
    """成本效果分析 (CEA)"""
    # TODO: 接入完整模型结果
    return {
        "model_id": model_id,
        "wtp_thresholds": wtp_thresholds,
        "recommendation": "模型运行后自动分析",
    }


@router.get("/models/{model_id}/report")
async def generate_report(
    model_id: str,
    mimo: MIMOClient = Depends(get_mimo_client),
):
    """生成 HEOR 报告"""
    prompt = f"""请基于模型 {model_id} 的结果，生成一份专业的HEOR分析报告。
包括：
1. 研究背景
2. 模型结构描述
3. 关键参数
4. 基础案例结果
5. 敏感性分析
6. 结论与建议"""

    try:
        report = await mimo.chat([
            {"role": "system", "content": "你是卫生经济学家，熟悉ISPOR指南和各国HTA要求。"},
            {"role": "user", "content": prompt},
        ])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"model_id": model_id, "report": report}
