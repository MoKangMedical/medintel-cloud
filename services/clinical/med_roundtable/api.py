"""
MedRoundTable 临床科研圆桌 — 整合版
源自 medroundtable 项目，适配 MedIntel Cloud monorepo
核心能力：14个Agent协作、A2A架构、科研全流程
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
import uuid
from datetime import datetime

from core.utils.mimo_client import get_mimo_client, MIMOClient

router = APIRouter()


# ==================== Agent 定义 ====================

class AgentRole(str, Enum):
    PI = "principal_investigator"           # 首席研究员
    BIOSTATISTICIAN = "biostatistician"      # 生物统计师
    EPIDEMIOLOGIST = "epidemiologist"        # 流行病学家
    CLINICIAN = "clinician"                  # 临床医生
    PHARMACOLOGIST = "pharmacologist"        # 药理学家
    GENETICIST = "geneticist"               # 遗传学家
    DATA_SCIENTIST = "data_scientist"        # 数据科学家
    LITERATURE_REVIEWER = "literature_reviewer"  # 文献审查员
    PROTOCOL_DESIGNER = "protocol_designer"  # 方案设计师
    ETHICS_REVIEWER = "ethics_reviewer"      # 伦理审查员
    PATIENT_ADVOCATE = "patient_advocate"    # 患者代言人
    REGULATORY_EXPERT = "regulatory_expert"  # 法规专家
    HEALTH_ECONOMIST = "health_economist"    # 卫生经济学家
    METHODOLOGIST = "methodologist"          # 方法学家


AGENT_PROMPTS = {
    AgentRole.PI: "你是首席研究员，负责统筹全局、协调各专家意见、形成最终结论。",
    AgentRole.BIOSTATISTICIAN: "你是生物统计师，负责研究设计的统计方法、样本量计算、分析方案。",
    AgentRole.EPIDEMIOLOGIST: "你是流行病学家，负责研究人群选择、偏倚控制、因果推断。",
    AgentRole.CLINICIAN: "你是临床医生，负责临床可行性评估、终点选择、患者安全。",
    AgentRole.PHARMACOLOGIST: "你是药理学家，负责药效机制、剂量选择、药物相互作用。",
    AgentRole.GENETICIST: "你是遗传学家，负责基因型分析、精准医学视角。",
    AgentRole.DATA_SCIENTIST: "你是数据科学家，负责数据管理方案、质量控制、分析管线。",
    AgentRole.LITERATURE_REVIEWER: "你是文献审查员，负责系统文献检索、证据综合。",
    AgentRole.PROTOCOL_DESIGNER: "你是方案设计师，负责研究方案撰写、流程优化。",
    AgentRole.ETHICS_REVIEWER: "你是伦理审查员，负责知情同意、弱势群体保护、风险评估。",
    AgentRole.PATIENT_ADVOCATE: "你是患者代言人，代表患者视角，关注可及性和体验。",
    AgentRole.REGULATORY_EXPERT: "你是法规专家，负责合规性审查、申报策略。",
    AgentRole.HEALTH_ECONOMIST: "你是卫生经济学家，负责成本效果分析、预算影响分析。",
    AgentRole.METHODOLOGIST: "你是方法学家，负责研究方法论、系统综述方法。",
}


# ==================== 数据模型 ====================

class RoundtableRequest(BaseModel):
    topic: str
    research_question: str
    context: Optional[str] = None
    agents: List[AgentRole] = Field(
        default_factory=lambda: list(AgentRole),
        description="参与讨论的Agent角色列表",
    )
    rounds: int = Field(default=3, ge=1, le=10, description="讨论轮数")
    model: Optional[str] = "mimo-v2-pro"


class AgentContribution(BaseModel):
    agent_role: str
    content: str
    timestamp: str


class RoundtableRound(BaseModel):
    round_number: int
    contributions: List[AgentContribution] = []
    summary: str = ""


class RoundtableResponse(BaseModel):
    session_id: str
    topic: str
    rounds: List[RoundtableRound] = []
    final_synthesis: str = ""
    key_recommendations: List[str] = []
    timestamp: str = ""


class ResearchProtocolRequest(BaseModel):
    research_question: str
    study_type: str = "interventional"  # observational, interventional, meta_analysis
    target_population: Optional[str] = None
    intervention: Optional[str] = None
    primary_outcome: Optional[str] = None
    model: Optional[str] = "mimo-v2-pro"


class ResearchProtocolResponse(BaseModel):
    protocol_id: str
    title: str
    sections: Dict[str, str] = {}
    agent_contributions: Dict[str, str] = {}


# ==================== API 端点 ====================

@router.get("/health")
async def health():
    return {
        "status": "ok", "service": "MedRoundTable", "version": "2.0.0",
        "agents": len(AgentRole),
        "architecture": "A2A (Agent-to-Agent)",
    }


@router.post("/discuss", response_model=RoundtableResponse)
async def roundtable_discuss(
    request: RoundtableRequest,
    mimo: MIMOClient = Depends(get_mimo_client),
):
    """多Agent圆桌讨论"""
    session_id = str(uuid.uuid4())
    rounds = []
    discussion_history = []

    for round_num in range(1, request.rounds + 1):
        contributions = []
        round_summaries = []

        for agent_role in request.agents:
            system_prompt = AGENT_PROMPTS[agent_role]

            # 构建上下文：前几轮讨论 + 其他Agent本轮已发言
            context_parts = [f"研究主题: {request.topic}"]
            context_parts.append(f"研究问题: {request.research_question}")
            if request.context:
                context_parts.append(f"背景: {request.context}")

            if discussion_history:
                context_parts.append("\n前几轮讨论摘要:")
                context_parts.extend(discussion_history[-3:])  # 最近3轮

            if round_summaries:
                context_parts.append("\n本轮其他专家已发表意见:")
                context_parts.extend(round_summaries)

            context_parts.append(f"\n请作为{agent_role.value}发表你的专业意见。第{round_num}轮讨论。")

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "\n".join(context_parts)},
            ]

            try:
                response = await mimo.chat(messages, model=request.model)
            except Exception:
                response = f"[{agent_role.value}] 暂无意见"

            contributions.append(AgentContribution(
                agent_role=agent_role.value,
                content=response,
                timestamp=datetime.now().isoformat(),
            ))
            round_summaries.append(f"【{agent_role.value}】: {response[:200]}...")

        # PI总结本轮
        pi_summary_prompt = f"请作为首席研究员，总结第{round_num}轮讨论的关键观点:\n" + "\n".join(round_summaries)
        try:
            round_summary = await mimo.chat([
                {"role": "system", "content": AGENT_PROMPTS[AgentRole.PI]},
                {"role": "user", "content": pi_summary_prompt},
            ], model=request.model)
        except Exception:
            round_summary = f"第{round_num}轮讨论完成。"

        rounds.append(RoundtableRound(
            round_number=round_num,
            contributions=contributions,
            summary=round_summary,
        ))
        discussion_history.append(f"第{round_num}轮: {round_summary[:300]}")

    # 最终综合
    synthesis_prompt = f"基于{request.rounds}轮讨论，形成最终综合意见和建议:\n" + "\n".join(discussion_history)
    try:
        final_synthesis = await mimo.chat([
            {"role": "system", "content": AGENT_PROMPTS[AgentRole.PI]},
            {"role": "user", "content": synthesis_prompt},
        ], model=request.model)
    except Exception:
        final_synthesis = "讨论完成，请查看各轮详细意见。"

    return RoundtableResponse(
        session_id=session_id,
        topic=request.topic,
        rounds=rounds,
        final_synthesis=final_synthesis,
        timestamp=datetime.now().isoformat(),
    )


@router.post("/protocol", response_model=ResearchProtocolResponse)
async def generate_protocol(
    request: ResearchProtocolRequest,
    mimo: MIMOClient = Depends(get_mimo_client),
):
    """AI辅助生成研究方案"""
    protocol_id = str(uuid.uuid4())
    sections = {}
    contributions = {}

    # 各Agent负责不同章节
    section_agents = {
        "研究背景": AgentRole.LITERATURE_REVIEWER,
        "研究目的": AgentRole.PI,
        "研究设计": AgentRole.PROTOCOL_DESIGNER,
        "研究人群": AgentRole.EPIDEMIOLOGIST,
        "干预措施": AgentRole.PHARMACOLOGIST,
        "结局指标": AgentRole.CLINICIAN,
        "样本量": AgentRole.BIOSTATISTICIAN,
        "统计分析": AgentRole.METHODOLOGIST,
        "伦理考量": AgentRole.ETHICS_REVIEWER,
        "预算评估": AgentRole.HEALTH_ECONOMIST,
    }

    for section_name, agent_role in section_agents.items():
        prompt = f"""请作为{agent_role.value}，撰写研究方案的「{section_name}」部分。

研究问题: {request.research_question}
研究类型: {request.study_type}
目标人群: {request.target_population or '待定'}
干预措施: {request.intervention or '待定'}
主要结局: {request.primary_outcome or '待定'}

请输出专业的方案文本。"""

        try:
            content = await mimo.chat([
                {"role": "system", "content": AGENT_PROMPTS[agent_role]},
                {"role": "user", "content": prompt},
            ], model=request.model)
        except Exception:
            content = f"[{section_name}] 待撰写"

        sections[section_name] = content
        contributions[agent_role.value] = section_name

    return ResearchProtocolResponse(
        protocol_id=protocol_id,
        title=f"关于「{request.research_question}」的研究方案",
        sections=sections,
        agent_contributions=contributions,
    )


@router.get("/agents")
async def list_agents():
    """列出所有可用Agent"""
    return {
        "total": len(AgentRole),
        "agents": [
            {"role": role.value, "description": AGENT_PROMPTS[role]}
            for role in AgentRole
        ],
    }
