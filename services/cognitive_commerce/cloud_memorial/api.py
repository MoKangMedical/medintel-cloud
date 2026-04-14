"""
🕊️ Cloud Memorial 云端纪念 — API 路由
语音克隆 + 视频通话 + 人格建模
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional

from core.utils.mimo_client import MIMOClient
from .service import VoiceCloningEngine, PersonaModelingEngine, VideoCallEngine, MemorialDataEngine

router = APIRouter()
mimo = MIMOClient()
voice_engine = VoiceCloningEngine(mimo)
persona_engine = PersonaModelingEngine(mimo)
video_engine = VideoCallEngine(mimo)
data_engine = MemorialDataEngine()


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


# ─── 语音克隆 ───────────────────────────────────────────────

class VoiceAnalyzeRequest(BaseModel):
    audio_description: str = Field(..., description="语音样本描述")


class VoiceSynthesizeRequest(BaseModel):
    text: str
    voice_profile: dict = Field(default_factory=dict)
    emotion: str = "neutral"


# ─── 人格建模 ───────────────────────────────────────────────

class PersonaBuildRequest(BaseModel):
    name: str
    relationship: str
    personality_traits: dict = Field(default_factory=dict)
    speaking_style: str = "自然亲切"
    memories: list[str] = Field(default_factory=list)
    media_descriptions: list[str] = Field(default_factory=list)


# ─── 视频通话 ───────────────────────────────────────────────

class VideoCallRequest(BaseModel):
    persona: dict
    user_message: str
    emotion: str = "neutral"
    scenario: str = "日常问候"


# ─── 纪念数据 ───────────────────────────────────────────────

class CreateMemorialRequest(BaseModel):
    name: str
    relationship: str
    personality_traits: dict = Field(default_factory=dict)
    speaking_style: str = "自然亲切"


class AddMaterialRequest(BaseModel):
    memorial_id: str
    material_type: str  # voice, photo, video, memory
    content: str


# ─── API 路由 ───────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok", service="CloudMemorial", version="1.0.0")


# 语音克隆
@router.post("/voice/analyze")
async def analyze_voice(req: VoiceAnalyzeRequest):
    """分析语音样本特征"""
    return await voice_engine.analyze_voice_sample(req.audio_description)


@router.post("/voice/synthesize")
async def synthesize_voice(req: VoiceSynthesizeRequest):
    """合成语音"""
    return await voice_engine.synthesize(req.text, req.voice_profile, req.emotion)


@router.get("/voice/voices")
async def list_voices():
    """可用语音列表"""
    return {"voices": voice_engine.list_available_voices()}


# 人格建模
@router.post("/persona/build")
async def build_persona(req: PersonaBuildRequest):
    """构建人格模型"""
    profile = req.model_dump()
    return await persona_engine.build_persona(profile, req.memories, req.media_descriptions)


@router.post("/persona/blueprint")
async def get_blueprint(req: PersonaBuildRequest):
    """生成对话系统提示词"""
    profile = req.model_dump()
    persona = await persona_engine.build_persona(profile, req.memories, req.media_descriptions)
    blueprint = persona_engine.build_prompt_blueprint(persona)
    return {"blueprint": blueprint, "persona_summary": persona.get("enhanced_description", "")}


# 视频通话
@router.post("/video/script")
async def generate_video_script(req: VideoCallRequest):
    """生成视频通话脚本"""
    return await video_engine.generate_video_script(req.persona, {"scenario": req.scenario, "emotion": req.emotion})


@router.post("/video/respond")
async def video_respond(req: VideoCallRequest):
    """视频通话回复"""
    return await video_engine.generate_response(req.persona, req.user_message, req.emotion)


# 纪念数据
@router.post("/memorials")
async def create_memorial(req: CreateMemorialRequest):
    """创建纪念档案"""
    return data_engine.create_memorial(req.model_dump())


@router.get("/memorials")
async def list_memorials():
    """纪念档案列表"""
    return {"memorials": data_engine.list_memorials()}


@router.get("/memorials/{memorial_id}")
async def get_memorial(memorial_id: str):
    """获取纪念档案详情"""
    result = data_engine.get_memorial(memorial_id)
    if not result:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="纪念档案不存在")
    return result


@router.post("/memorials/materials")
async def add_material(req: AddMaterialRequest):
    """添加素材"""
    return data_engine.add_material(req.memorial_id, req.material_type, req.content)
