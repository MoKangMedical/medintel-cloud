"""
💄 MediSlim 消费医疗平台 — API 路由
AI体质评估 + 智能营销 + 智能客服 + 数据分析
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from core.utils.mimo_client import MIMOClient
from .service import ConstitutionEngine, RecommendationEngine, CustomerServiceEngine, DataAnalyticsEngine

router = APIRouter()

# 服务实例
constitution_engine = ConstitutionEngine()
mimo_client = MIMOClient()
recommendation_engine = RecommendationEngine(mimo=mimo_client)
customer_service = CustomerServiceEngine(mimo=mimo_client)
analytics = DataAnalyticsEngine()


# ─── 数据模型 ───────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class AssessmentRequest(BaseModel):
    answers: dict[str, int] = Field(..., description="问题ID → 得分(1-5)")
    goals: list[str] = Field(default_factory=list, description="健康目标")


class AssessmentResponse(BaseModel):
    primary_type: str
    primary_score: float = 0
    secondary_types: list[dict] = []
    scores: dict[str, float] = {}
    characteristics: str = ""
    tcm_principles: list[str] = []
    health_risks: list[str] = []
    dietary_suggestions: list[str] = []
    exercise_recommendations: list[str] = []
    recommendations: list[dict] = []


class AIAssessRequest(BaseModel):
    goals: list[str] = Field(..., description="健康目标列表")


class RecommendationRequest(BaseModel):
    constitution: str
    goals: list[str] = Field(default_factory=list)


class ChatRequest(BaseModel):
    message: str
    customer_id: Optional[str] = None
    context: Optional[dict] = None


class ChatResponse(BaseModel):
    response: str
    intent: str
    sentiment: str
    source: str
    escalate: bool = False


class SegmentRequest(BaseModel):
    age: Optional[int] = 30
    gender: Optional[str] = None
    goals: list[str] = Field(default_factory=list)
    constitution: Optional[str] = None


class CampaignRequest(BaseModel):
    segment: str
    product_name: str
    channel: str = "wechat"


class CampaignResponse(BaseModel):
    content: str
    segment: str
    product_name: str


# ─── API 路由 ───────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok", service="MediSlim", version="1.0.0")


@router.get("/questionnaire")
async def get_questionnaire():
    """获取体质评估问卷"""
    return {"questions": constitution_engine.get_questionnaire(), "count": 16}


@router.post("/assess", response_model=AssessmentResponse)
async def assess_constitution(req: AssessmentRequest):
    """体质评估 — 基于问卷答案"""
    result = constitution_engine.assess(req.answers)
    recs = recommendation_engine.recommend_by_constitution(
        result["primary_type"], req.goals
    )
    return AssessmentResponse(**result, recommendations=recs)


@router.post("/assess-ai")
async def ai_assess(req: AIAssessRequest):
    """AI 体质推断 — 基于健康目标"""
    result = await constitution_engine.ai_assess(req.goals, mimo_client)
    recs = recommendation_engine.recommend_by_constitution(
        result.get("primary_type", "平和质"), req.goals
    )
    return {**result, "recommendations": recs}


@router.post("/recommend")
async def recommend(req: RecommendationRequest):
    """产品推荐"""
    return {"recommendations": recommendation_engine.recommend_by_constitution(req.constitution, req.goals)}


@router.post("/customer/segment")
async def segment_customer(req: SegmentRequest):
    """客户分群"""
    profile = req.model_dump()
    segment = recommendation_engine.customer_segment(profile)
    return {**segment, "profile": profile}


@router.post("/campaign/generate", response_model=CampaignResponse)
async def generate_campaign(req: CampaignRequest):
    """AI 生成营销文案"""
    content = await recommendation_engine.generate_campaign_content(req.segment, req.product_name)
    return CampaignResponse(content=content, segment=req.segment, product_name=req.product_name)


@router.post("/customer-service/chat", response_model=ChatResponse)
async def customer_chat(req: ChatRequest):
    """智能客服对话"""
    result = await customer_service.respond(req.message, req.context)
    return ChatResponse(**result)


@router.get("/products")
async def list_products():
    """产品目录"""
    from .service import PRODUCT_CATALOG
    return {"products": list(PRODUCT_CATALOG.values())}


@router.get("/analytics/dashboard")
async def get_dashboard():
    """数据分析仪表盘"""
    return analytics.get_dashboard()
