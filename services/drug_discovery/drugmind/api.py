"""
🤖 DrugMind API — 数字分身协作 · 决策追踪 · Second Me集成
整合自 DrugMind 项目
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

logger = logging.getLogger(__name__)
router = APIRouter()

# Global instances (in production use dependency injection)
from .digital_twin.engine import DigitalTwinEngine
from .digital_twin.roles import list_roles
from .collaboration.decision_log import DecisionLogger
from .collaboration.consensus import ConsensusEngine
from .collaboration.discussion import DiscussionEngine
from .second_me.integration import SecondMeIntegration

twin_engine = DigitalTwinEngine()
decision_logger = DecisionLogger()
consensus_engine = ConsensusEngine()


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class CreateTwinRequest(BaseModel):
    role_id: str = Field(..., description="角色ID")
    name: str = Field(..., description="分身名称")
    custom_expertise: Optional[list[str]] = None


class AskTwinRequest(BaseModel):
    twin_id: str
    question: str
    context: str = ""
    temperature: float = Field(0.4, ge=0, le=2)


class TeachRequest(BaseModel):
    twin_id: str
    content: str
    source: str = ""


class DiscussionRequest(BaseModel):
    topic: str
    participant_ids: list[str]
    context: str = ""
    max_rounds: int = Field(2, ge=1, le=5)


class DebateRequest(BaseModel):
    topic: str
    participant_ids: list[str]
    question: str
    context: str = ""


class DecisionRequest(BaseModel):
    topic: str
    decision: str  # GO / NO-GO / CONDITIONAL
    rationale: str
    participants: list[str]
    opinions: list[dict]
    dissenting: Optional[list[str]] = None
    conditions: Optional[list[str]] = None


class VoteRequest(BaseModel):
    topic: str
    options: list[str]
    votes: dict[str, str]
    weights: Optional[dict[str, float]] = None


class SecondMeRequest(BaseModel):
    name: str
    role: str
    expertise: list[str]
    knowledge: Optional[list[str]] = None
    personality: str = "balanced"
    mode: str = "cloud"


class ChatRequest(BaseModel):
    instance_id: str
    message: str


# ─── Endpoints ───

@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok", service="DrugMind", version="1.0.0")


@router.get("/roles")
async def get_roles():
    """获取所有药物研发角色"""
    return {"roles": list_roles(), "count": len(list_roles())}


@router.post("/twins/create")
async def create_twin(request: CreateTwinRequest):
    """创建数字分身"""
    try:
        result = twin_engine.create_twin(
            role_id=request.role_id, name=request.name,
            custom_expertise=request.custom_expertise,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/twins/ask")
async def ask_twin(request: AskTwinRequest):
    """向数字分身提问"""
    response = twin_engine.ask_twin(
        twin_id=request.twin_id, question=request.question,
        context=request.context, temperature=request.temperature,
    )
    return {"twin_id": response.twin_id, "name": response.name, "role": response.role,
            "emoji": response.emoji, "message": response.message,
            "confidence": response.confidence, "reasoning": response.reasoning}


@router.post("/twins/teach")
async def teach_twin(request: TeachRequest):
    """教数字分身新知识"""
    twin_engine.teach_twin(twin_id=request.twin_id, content=request.content, source=request.source)
    return {"status": "taught", "twin_id": request.twin_id}


@router.get("/twins")
async def list_twins():
    """列出所有数字分身"""
    return {"twins": twin_engine.list_twins()}


@router.get("/twins/{twin_id}/memory")
async def get_twin_memory(twin_id: str, query: str = ""):
    """获取分身记忆"""
    return {"twin_id": twin_id, "memories": twin_engine.get_twin_memory(twin_id, query)}


@router.post("/discussions")
async def create_discussion(request: DiscussionRequest):
    """创建讨论会话"""
    disc = DiscussionEngine(twin_engine)
    session = disc.create_discussion(
        topic=request.topic, participant_ids=request.participant_ids, context=request.context,
    )
    messages = disc.run_round_robin(session.session_id, context=request.context,
                                     max_rounds=request.max_rounds)
    summary = disc.summarize_discussion(session.session_id)
    return {"session_id": session.session_id, "topic": session.topic,
            "messages_count": len(messages), "summary": summary}


@router.post("/debate")
async def create_debate(request: DebateRequest):
    """角色辩论模式"""
    disc = DiscussionEngine(twin_engine)
    session = disc.create_discussion(
        topic=request.topic, participant_ids=request.participant_ids, context=request.context,
    )
    debate = disc.run_debate(session.session_id, question=request.question, context=request.context)
    return {"session_id": session.session_id, **debate}


@router.post("/decisions")
async def log_decision(request: DecisionRequest):
    """记录Go/No-Go决策"""
    record = decision_logger.log_decision(
        topic=request.topic, decision=request.decision, rationale=request.rationale,
        participants=request.participants, opinions=request.opinions,
        dissenting=request.dissenting, conditions=request.conditions,
    )
    return {"decision_id": record.decision_id, "decision": record.decision, "topic": record.topic}


@router.get("/decisions")
async def get_decisions(topic: str = ""):
    """获取决策历史"""
    return {"decisions": decision_logger.get_decision_history(topic)}


@router.post("/consensus")
async def vote_consensus(request: VoteRequest):
    """投票共识"""
    result = consensus_engine.vote(
        topic=request.topic, options=request.options,
        votes=request.votes, weights=request.weights,
    )
    return {"topic": result.topic, "final_decision": result.final_decision,
            "confidence": result.confidence, "vote_distribution": result.vote_distribution,
            "dissenting": result.dissenting_opinions}


@router.post("/secondme/create")
async def create_second_me(request: SecondMeRequest):
    """创建Second Me数字分身"""
    sm = SecondMeIntegration(mode=request.mode)
    result = sm.create_pharma_twin(
        name=request.name, role=request.role, expertise=request.expertise,
        knowledge=request.knowledge, personality=request.personality,
    )
    return result


@router.post("/secondme/chat")
async def chat_second_me(request: ChatRequest):
    """与Second Me分身对话"""
    sm = SecondMeIntegration()
    result = sm.chat(instance_id=request.instance_id, message=request.message)
    return result
