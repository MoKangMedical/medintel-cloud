"""
Biostats 生物统计 — 整合版
源自 Biostats 项目
核心能力：统计分析、样本量计算、生存分析
"""

from fastapi import Depends, APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from enum import Enum

from core.utils.mimo_client import get_mimo_client, MIMOClient

router = APIRouter()


class AnalysisType(str, Enum):
    DESCRIPTIVE = "descriptive"
    T_TEST = "t_test"
    CHI_SQUARE = "chi_square"
    ANOVA = "anova"
    REGRESSION = "regression"
    SURVIVAL = "survival"
    META_ANALYSIS = "meta_analysis"
    SAMPLE_SIZE = "sample_size"


class SampleSizeRequest(BaseModel):
    study_type: str  # rct, cohort, case_control, diagnostic
    effect_size: float
    alpha: float = 0.05
    power: float = 0.80
    allocation_ratio: float = 1.0
    dropout_rate: float = 0.10


class SampleSizeResult(BaseModel):
    n_per_group: int
    total_n: int
    adjusted_total_n: int
    assumptions: Dict[str, float] = {}


class SurvivalAnalysisRequest(BaseModel):
    time: List[float]
    event: List[int]  # 1=event, 0=censored
    group: Optional[List[str]] = None
    method: str = "kaplan_meier"  # kaplan_meier, cox, parametric


class StatisticalTestRequest(BaseModel):
    data: Dict[str, List[float]]
    test_type: AnalysisType
    alpha: float = 0.05
    alternative: str = "two-sided"  # two-sided, greater, less


class StatisticalTestResult(BaseModel):
    test_type: str
    statistic: float
    p_value: float
    ci_lower: Optional[float] = None
    ci_upper: Optional[float] = None
    significant: bool
    interpretation: str = ""


@router.get("/health")
async def health():
    return {"status": "ok", "service": "Biostats", "version": "1.0.0",
            "analyses": [t.value for t in AnalysisType]}


@router.post("/sample-size", response_model=SampleSizeResult)
async def calculate_sample_size(request: SampleSizeRequest):
    """样本量计算"""
    import numpy as np
    from scipy import stats

    z_alpha = stats.norm.ppf(1 - request.alpha / 2)
    z_beta = stats.norm.ppf(request.power)

    if request.study_type == "rct":
        n_per_group = ((z_alpha + z_beta) ** 2) * 2 / (request.effect_size ** 2)
    elif request.study_type == "cohort":
        p1 = 0.3
        p2 = p1 * request.effect_size
        n_per_group = ((z_alpha * np.sqrt(2 * p1 * (1 - p1))) + z_beta * np.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2 / ((p1 - p2) ** 2)
    else:
        n_per_group = ((z_alpha + z_beta) ** 2) * 2 / (request.effect_size ** 2)

    n_per_group = int(np.ceil(n_per_group))
    total_n = int(n_per_group * (1 + 1 / request.allocation_ratio))
    adjusted = int(np.ceil(total_n / (1 - request.dropout_rate)))

    return SampleSizeResult(
        n_per_group=n_per_group,
        total_n=total_n,
        adjusted_total_n=adjusted,
        assumptions={"z_alpha": round(z_alpha, 3), "z_beta": round(z_beta, 3)},
    )


@router.post("/test", response_model=StatisticalTestResult)
async def run_statistical_test(request: StatisticalTestRequest):
    """运行统计检验"""
    import numpy as np
    from scipy import stats

    data = request.data
    keys = list(data.keys())

    if request.test_type == AnalysisType.T_TEST and len(keys) >= 2:
        stat, p = stats.ttest_ind(data[keys[0]], data[keys[1]], alternative=request.alternative)
        ci = stats.ttest_ind(data[keys[0]], data[keys[1]]).confidence_interval()
        return StatisticalTestResult(
            test_type="t_test", statistic=round(stat, 4), p_value=round(p, 6),
            ci_lower=round(ci.low, 4), ci_upper=round(ci.high, 4),
            significant=p < request.alpha,
            interpretation=f"{'拒绝' if p < request.alpha else '无法拒绝'}零假设 (α={request.alpha})",
        )
    elif request.test_type == AnalysisType.CHI_SQUARE:
        observed = np.array([data[k] for k in keys])
        stat, p, dof, expected = stats.chi2_contingency(observed)
        return StatisticalTestResult(
            test_type="chi_square", statistic=round(stat, 4), p_value=round(p, 6),
            significant=p < request.alpha,
            interpretation=f"自由度={dof}, {'关联显著' if p < request.alpha else '无显著关联'}",
        )
    elif request.test_type == AnalysisType.ANOVA:
        groups = [data[k] for k in keys]
        stat, p = stats.f_oneway(*groups)
        return StatisticalTestResult(
            test_type="anova", statistic=round(stat, 4), p_value=round(p, 6),
            significant=p < request.alpha,
            interpretation=f"{'组间差异显著' if p < request.alpha else '组间无显著差异'}",
        )
    else:
        raise HTTPException(status_code=400, detail=f"不支持的检验类型: {request.test_type.value}")


@router.post("/survival")
async def survival_analysis(request: SurvivalAnalysisRequest):
    """生存分析"""
    # TODO: 接入 lifelines 库
    return {
        "method": request.method,
        "median_survival": None,
        "hazard_ratio": None,
        "log_rank_p": None,
        "message": "生存分析模块待接入 lifelines 库",
    }


@router.post("/meta-analysis")
async def meta_analysis(
    studies: List[Dict[str, float]],
    mimo: MIMOClient = Depends(get_mimo_client),
):
    """Meta分析"""
    # TODO: 实现固定效应和随机效应模型
    return {
        "n_studies": len(studies),
        "pooled_effect": None,
        "heterogeneity_i2": None,
        "message": "Meta分析模块待完善",
    }
