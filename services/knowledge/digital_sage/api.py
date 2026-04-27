"""
DigitalSage 100大脑对话 — 整合版
源自 digital-sage 项目，适配 MedIntel Cloud monorepo
核心能力：100个名人方法论、AI对话引擎、思想画像
"""

from fastapi import Depends, APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from enum import Enum
import uuid
from datetime import datetime

from core.utils.mimo_client import get_mimo_client, MIMOClient

router = APIRouter()


class SageCategory(str, Enum):
    PHILOSOPHY = "philosophy"
    SCIENCE = "science"
    BUSINESS = "business"
    MEDICINE = "medicine"
    ARTS = "arts"
    LEADERSHIP = "leadership"
    INNOVATION = "innovation"
    PSYCHOLOGY = "psychology"


class SageProfile(BaseModel):
    id: str
    name: str
    name_zh: str
    category: SageCategory
    era: str
    methodology: str
    core_ideas: List[str] = []
    thinking_framework: str
    avatar_url: Optional[str] = None


class ChatRequest(BaseModel):
    sage_id: str
    message: str
    conversation_id: Optional[str] = None
    model: Optional[str] = "mimo-v2-pro"


class ChatResponse(BaseModel):
    conversation_id: str
    sage_id: str
    sage_name: str
    response: str
    methodology_applied: str = ""
    related_sages: List[str] = []


class ThoughtComparisonRequest(BaseModel):
    topic: str
    sage_ids: List[str] = Field(..., min_length=2, max_length=5)


class ThoughtComparisonResponse(BaseModel):
    topic: str
    perspectives: Dict[str, str] = {}
    synthesis: str = ""
    common_ground: List[str] = []
    key_differences: List[str] = []


# ==================== 名人数据库 ====================

SAGE_DATABASE = [
    SageProfile(id="socrates", name="Socrates", name_zh="苏格拉底", category=SageCategory.PHILOSOPHY,
                era="469-399 BC", methodology="苏格拉底式提问法", core_ideas=["认识你自己", "美德即知识", "无知之知"],
                thinking_framework="通过连续追问暴露矛盾，引导对方自行发现真理"),
    SageProfile(id="aristotle", name="Aristotle", name_zh="亚里士多德", category=SageCategory.PHILOSOPHY,
                era="384-322 BC", methodology="三段论逻辑", core_ideas=["第一性原理", "中庸之道", "四因说"],
                thinking_framework="从基本原理出发进行演绎推理"),
    SageProfile(id="confucius", name="Confucius", name_zh="孔子", category=SageCategory.PHILOSOPHY,
                era="551-479 BC", methodology="因材施教", core_ideas=["仁义礼智信", "中庸之道", "有教无类"],
                thinking_framework="以德化人，以礼治国，知行合一"),
    SageProfile(id="einstein", name="Albert Einstein", name_zh="爱因斯坦", category=SageCategory.SCIENCE,
                era="1879-1955", methodology="思想实验", core_ideas=["相对论", "质能方程", "统一场论"],
                thinking_framework="从物理直觉出发，用数学验证，追求简洁优美的理论"),
    SageProfile(id="darwin", name="Charles Darwin", name_zh="达尔文", category=SageCategory.SCIENCE,
                era="1809-1882", methodology="归纳推理+长期观察", core_ideas=["自然选择", "适者生存", "共同祖先"],
                thinking_framework="海量观察→模式识别→理论构建→反复验证"),
    SageProfile(id="jobs", name="Steve Jobs", name_zh="乔布斯", category=SageCategory.BUSINESS,
                era="1955-2011", methodology="极简设计思维", core_ideas=["用户体验至上", "跨界创新", "现实扭曲力场"],
                thinking_framework="从用户本质需求出发，追求极致简约"),
    SageProfile(id="musk", name="Elon Musk", name_zh="马斯克", category=SageCategory.INNOVATION,
                era="1971-", methodology="第一性原理+五步工作法", core_ideas=["物理学思维", "快速迭代", "跨领域整合"],
                thinking_framework="将问题拆解到物理基本原理，从头推导解决方案"),
    SageProfile(id="kahneman", name="Daniel Kahneman", name_zh="卡尼曼", category=SageCategory.PSYCHOLOGY,
                era="1934-2024", methodology="双系统理论", core_ideas=["系统1/系统2", "锚定效应", "损失厌恶"],
                thinking_framework="人类决策存在系统性偏见，通过实验揭示认知模式"),
    SageProfile(id="da_vinci", name="Leonardo da Vinci", name_zh="达芬奇", category=SageCategory.ARTS,
                era="1452-1519", methodology="跨学科观察", core_ideas=["艺术即科学", "观察即理解", "好奇心驱动"],
                thinking_framework="通过细致观察自然，将艺术、科学、工程融为一体"),
    SageProfile(id="hippocrates", name="Hippocrates", name_zh="希波克拉底", category=SageCategory.MEDICINE,
                era="460-370 BC", methodology="临床观察+体液学说", core_ideas=["首先，不伤害", "自然治愈力", "整体观"],
                thinking_framework="基于细致的临床观察，强调自然治愈力和整体观"),
    # ... 可扩展到100个
]


@router.get("/health")
async def health():
    return {"status": "ok", "service": "DigitalSage", "version": "2.0.0",
            "sages": len(SAGE_DATABASE)}


@router.get("/sages", response_model=List[SageProfile])
async def list_sages(
    category: Optional[SageCategory] = None,
    search: Optional[str] = None,
):
    """列出所有智者"""
    sages = SAGE_DATABASE
    if category:
        sages = [s for s in sages if s.category == category]
    if search:
        sages = [s for s in sages if search.lower() in s.name.lower() or search in s.name_zh]
    return sages


@router.get("/sages/{sage_id}", response_model=SageProfile)
async def get_sage(sage_id: str):
    """获取智者详情"""
    for sage in SAGE_DATABASE:
        if sage.id == sage_id:
            return sage
    raise HTTPException(status_code=404, detail="智者未找到")


@router.post("/chat", response_model=ChatResponse)
async def chat_with_sage(
    request: ChatRequest,
    mimo: MIMOClient = Depends(get_mimo_client),
):
    """与智者对话"""
    sage = None
    for s in SAGE_DATABASE:
        if s.id == request.sage_id:
            sage = s
            break
    if not sage:
        raise HTTPException(status_code=404, detail="智者未找到")

    system_prompt = f"""你是{sage.name}（{sage.name_zh}），{sage.era}的{sage.category.value}大师。
你的方法论：{sage.methodology}
你的核心思想：{', '.join(sage.core_ideas)}
你的思维方式：{sage.thinking_framework}

请以{sage.name}的视角、风格和方法论来回应。用第一人称，体现其独特的思维方式。
如果讨论现代话题，想象{sage.name}会如何用其经典方法论来分析。"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": request.message},
    ]

    try:
        response = await mimo.chat(messages, model=request.model)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return ChatResponse(
        conversation_id=request.conversation_id or str(uuid.uuid4()),
        sage_id=sage.id,
        sage_name=sage.name,
        response=response,
        methodology_applied=sage.methodology,
        timestamp=datetime.now().isoformat(),
    )


@router.post("/compare", response_model=ThoughtComparisonResponse)
async def compare_thinkers(
    request: ThoughtComparisonRequest,
    mimo: MIMOClient = Depends(get_mimo_client),
):
    """跨思想家比较"""
    perspectives = {}
    for sage_id in request.sage_ids:
        sage = next((s for s in SAGE_DATABASE if s.id == sage_id), None)
        if not sage:
            continue

        prompt = f"""请以{sage.name}（{sage.name_zh}）的视角来分析以下主题：
主题：{request.topic}
方法论：{sage.methodology}
核心思想：{', '.join(sage.core_ideas)}"""

        try:
            perspective = await mimo.chat([
                {"role": "system", "content": f"你是{sage.name}，请用你的方法论来分析问题。"},
                {"role": "user", "content": prompt},
            ])
            perspectives[sage.name] = perspective
        except Exception:
            pass

    # 综合分析
    all_perspectives = "\n".join(f"【{k}】{v[:300]}" for k, v in perspectives.items())
    try:
        synthesis = await mimo.chat([
            {"role": "system", "content": "你是思想比较专家，综合不同思想家的观点。"},
            {"role": "user", "content": f"请综合比较以下思想家对「{request.topic}」的观点:\n{all_perspectives}"},
        ])
    except Exception:
        synthesis = "比较分析完成。"

    return ThoughtComparisonResponse(
        topic=request.topic,
        perspectives=perspectives,
        synthesis=synthesis,
    )
