"""
🔍 天眼 Tianyan — API 路由
多Agent人群模拟 + 商业预测
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional

from core.utils.mimo_client import MIMOClient
from .service import SimulationEngine, BusinessPredictionEngine, SyntheticPopulation

router = APIRouter()
mimo = MIMOClient()
sim_engine = SimulationEngine(mimo=mimo)
prediction_engine = BusinessPredictionEngine(mimo=mimo)
population_factory = SyntheticPopulation()


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


# ─── 人群模拟 ───────────────────────────────────────────────

class SimulationConfig(BaseModel):
    population_size: int = Field(default=100, ge=10, le=500)
    scenario: str = Field(..., description="模拟场景描述")
    constraints: Optional[dict] = Field(default=None, description="人群约束条件")
    rounds: int = Field(default=1, ge=1, le=10)
    seed: Optional[int] = None


class PopulationGenerateRequest(BaseModel):
    n: int = Field(default=100, ge=1, le=500)
    constraints: Optional[dict] = None


# ─── 商业预测 ───────────────────────────────────────────────

class MarketSizingRequest(BaseModel):
    product_description: str
    target_market: str


class CompetitiveAnalysisRequest(BaseModel):
    company: str
    competitors: list[str]


class RevenueForecastRequest(BaseModel):
    historical_data: list[float] = Field(..., description="历史收入数据")
    periods: int = Field(default=4, ge=1, le=12)


# ─── API 路由 ───────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok", service="Tianyan", version="1.0.0")


# 人群模拟
@router.post("/population/generate")
async def generate_population(req: PopulationGenerateRequest):
    """生成合成人群"""
    profiles = population_factory.generate(req.n, req.constraints)
    return {
        "count": len(profiles),
        "profiles": [
            {
                "agent_id": p.agent_id, "age": p.age, "gender": p.gender,
                "city": p.city, "city_tier": p.city_tier,
                "monthly_income": p.monthly_income,
                "consumer_archetype": p.consumer_archetype,
                "digital_literacy": p.digital_literacy,
                "price_sensitivity": p.price_sensitivity,
                "health_consciousness": p.health_consciousness,
            }
            for p in profiles[:20]  # 返回前20个预览
        ],
        "summary": {
            "avg_age": round(sum(p.age for p in profiles) / len(profiles), 1) if profiles else 0,
            "avg_income": round(sum(p.monthly_income for p in profiles) / len(profiles)) if profiles else 0,
            "gender_dist": {
                "男": sum(1 for p in profiles if p.gender == "男"),
                "女": sum(1 for p in profiles if p.gender == "女"),
            },
        },
    }


@router.post("/simulation/run")
async def run_simulation(config: SimulationConfig):
    """运行人群模拟"""
    result = await sim_engine.run_simulation(config.model_dump())
    return result


@router.get("/simulation/{sim_id}")
async def get_simulation(sim_id: str):
    """获取模拟结果"""
    result = sim_engine.get_simulation(sim_id)
    if not result:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="模拟不存在")
    return result


@router.get("/simulations")
async def list_simulations():
    """模拟历史列表"""
    return {"simulations": sim_engine.list_simulations()}


# 商业预测
@router.post("/market/sizing")
async def market_sizing(req: MarketSizingRequest):
    """市场规模预测"""
    return await prediction_engine.market_sizing(req.product_description, req.target_market)


@router.post("/market/competitive")
async def competitive_analysis(req: CompetitiveAnalysisRequest):
    """竞品分析"""
    return await prediction_engine.competitive_analysis(req.company, req.competitors)


@router.post("/market/revenue-forecast")
async def revenue_forecast(req: RevenueForecastRequest):
    """收入预测"""
    return prediction_engine.forecast_revenue(req.historical_data, req.periods)
