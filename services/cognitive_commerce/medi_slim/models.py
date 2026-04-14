"""
💄 MediSlim 数据模型 — AI体质评估、智能营销、客服
"""

from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


# ─── 体质评估 ───────────────────────────────────────────────

class ConstitutionType(str, Enum):
    """中医体质九分法"""
    PING_HE = "平和质"
    QI_XU = "气虚质"
    YANG_XU = "阳虚质"
    YIN_XU = "阴虚质"
    TAN_SHI = "痰湿质"
    SHI_RE = "湿热质"
    XUE_YU = "血瘀质"
    QI_YU = "气郁质"
    TE_BING = "特禀质"


class AssessmentQuestion(BaseModel):
    id: str
    category: str
    text: str
    options: list[str] = []
    weight: float = 1.0


class AssessmentRequest(BaseModel):
    patient_id: Optional[str] = None
    answers: dict[str, int] = Field(..., description="问题ID → 得分(1-5)")
    age: Optional[int] = None
    gender: Optional[str] = None
    lifestyle: Optional[dict] = None


class ConstitutionResult(BaseModel):
    primary_type: ConstitutionType
    secondary_types: list[dict] = []  # [{type, score}]
    scores: dict[str, float] = {}
    health_risks: list[str] = []
    dietary_suggestions: list[str] = []
    exercise_recommendations: list[str] = []
    tcm_principles: list[str] = []
    confidence: float = 0.0
    assessed_at: datetime = Field(default_factory=datetime.now)


# ─── 智能营销 ───────────────────────────────────────────────

class CustomerSegment(str, Enum):
    HEALTH_CONSCIOUS = "健康关注型"
    BEAUTY_SEEKER = "美容需求型"
    CHRONIC_MANAGE = "慢病管理型"
    ELDER_CARE = "老年养护型"
    POST_PARTUM = "产后恢复型"
    WEIGHT_MANAGE = "体重管理型"


class MarketingCampaign(BaseModel):
    id: str
    name: str
    target_segments: list[CustomerSegment] = []
    channel: str = "wechat"  # wechat, sms, app_push, email
    content_template: str = ""
    product_ids: list[str] = []
    status: str = "draft"
    created_at: datetime = Field(default_factory=datetime.now)


class PersonalizedRecommendation(BaseModel):
    customer_id: str
    segment: CustomerSegment
    products: list[dict] = []
    content: str = ""
    predicted_conversion: float = 0.0
    channel_preference: str = "wechat"
    best_send_time: Optional[str] = None


# ─── 智能客服 ───────────────────────────────────────────────

class ServiceChannel(str, Enum):
    WECHAT = "wechat"
    PHONE = "phone"
    LIVECHAT = "livechat"
    MINIAPP = "miniapp"


class ServiceTicket(BaseModel):
    id: str
    customer_id: str
    channel: ServiceChannel
    category: Optional[str] = None  # product_inquiry, complaint, consultation, after_sales
    subject: str = ""
    messages: list[dict] = []
    status: str = "open"  # open, in_progress, resolved, escalated
    sentiment: Optional[str] = None  # positive, neutral, negative
    priority: str = "normal"
    assigned_to: Optional[str] = None
    resolution: Optional[str] = None
    satisfaction_score: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None


class ChatMessage(BaseModel):
    role: str  # user, assistant, agent
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Optional[dict] = None


class CustomerServiceRequest(BaseModel):
    ticket_id: Optional[str] = None
    customer_id: str
    message: str
    channel: ServiceChannel = ServiceChannel.WECHAT
    context: Optional[dict] = None
