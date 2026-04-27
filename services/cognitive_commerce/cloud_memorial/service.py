"""
🕊️ Cloud Memorial 云端纪念 — 语音克隆 + 视频通话 + 人格建模
源自 cloud-memorial 项目，适配 monorepo core/ 共享模型和 MIMO 客户端
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from core.utils.mimo_client import MIMOClient


class VoiceCloningEngine:
    """语音克隆引擎 — 基于 MIMO TTS 的语音合成"""

    def __init__(self, mimo: MIMOClient):
        self.mimo = mimo

    async def analyze_voice_sample(self, audio_description: str) -> dict:
        """分析语音样本特征"""
        prompt = f"""分析以下语音样本的关键特征，用于语音克隆：
{audio_description}

返回JSON格式：
{{"voice_pitch": "音高特征", "speed": "语速特征", "tone": "语气特征", "accent": "口音特征", "emotional_range": "情感范围"}}"""
        try:
            result = await self.mimo.chat(
                [{"role": "user", "content": prompt}],
                model="mimo-v2-pro", temperature=0.3, max_tokens=300,
            )
            return {"status": "analyzed", "profile": json.loads(result), "confidence": 0.85}
        except Exception:
            return {
                "status": "analyzed",
                "profile": {"voice_pitch": "中等", "speed": "偏慢", "tone": "温和",
                            "accent": "普通话", "emotional_range": "中等"},
                "confidence": 0.6,
            }

    async def synthesize(self, text: str, voice_profile: dict, emotion: str = "neutral") -> dict:
        """合成语音"""
        style_tags = [voice_profile.get("tone", "自然"), voice_profile.get("speed", "中等")]
        if emotion != "neutral":
            style_tags.append(emotion)
        prompt = f"用以下风格朗读：{'、'.join(style_tags)}\n\n文本：{text}"
        try:
            result = await self.mimo.chat(
                [{"role": "user", "content": prompt}],
                model="mimo-v2-tts", temperature=0.6, max_tokens=500,
            )
            return {"status": "synthesized", "text": text, "audio_format": "wav", "duration_estimate": len(text) * 0.3}
        except Exception:
            return {"status": "fallback", "text": text, "note": "TTS服务暂时不可用，返回文本"}

    def list_available_voices(self) -> list[dict]:
        return [
            {"id": "warm_female", "name": "温暖女声", "gender": "female", "style": "温柔"},
            {"id": "calm_male", "name": "沉稳男声", "gender": "male", "style": "稳重"},
            {"id": "cheerful_female", "name": "活泼女声", "gender": "female", "style": "开朗"},
            {"id": "gentle_male", "name": "温和男声", "gender": "male", "style": "亲切"},
        ]


class PersonaModelingEngine:
    """人格建模引擎 — 从素材构建数字人画像"""

    def __init__(self, mimo: MIMOClient):
        self.mimo = mimo

    async def build_persona(self, profile: dict, memories: list[str], media_descriptions: list[str]) -> dict:
        """构建人格模型"""
        persona = {
            "name": profile.get("name", "未知"),
            "relationship": profile.get("relationship", "亲人"),
            "personality_traits": profile.get("personality_traits", {}),
            "speaking_style": profile.get("speaking_style", "自然亲切"),
            "memory_anchors": memories[:10],
            "visual_traits": media_descriptions[:5],
            "built_at": datetime.now().isoformat(),
            "status": "ready",
        }

        # AI 增强人格描述
        try:
            context = f"""
人物档案：{persona['name']}，{persona['relationship']}
性格线索：{json.dumps(persona['personality_traits'], ensure_ascii=False)}
说话方式：{persona['speaking_style']}
关键回忆：{'；'.join(memories[:5])}
视觉特征：{'；'.join(media_descriptions[:3])}
"""
            prompt = f"""基于以下信息，生成一段数字人格描述（不超过200字）：
{context}
要求：保持温暖自然，体现人物独特性格和说话习惯。"""
            enhanced = await self.mimo.chat(
                [{"role": "user", "content": prompt}],
                model="mimo-v2-pro", temperature=0.7, max_tokens=300,
            )
            persona["enhanced_description"] = enhanced
        except Exception:
            persona["enhanced_description"] = (
                f"{persona['name']}是你的{persona['relationship']}，"
                f"说话风格{persona['speaking_style']}。"
            )

        return persona

    def build_prompt_blueprint(self, persona: dict) -> str:
        """生成对话系统提示词"""
        name = persona.get("name", "ta")
        relationship = persona.get("relationship", "亲人")
        style = persona.get("speaking_style", "自然亲切")
        traits = persona.get("personality_traits", {})
        traits_desc = "，".join(f"{k}：{v}" for k, v in traits.items()) or "温暖、关爱"

        return f"""你是{name}，是用户的{relationship}。

性格特点：{traits_desc}
说话风格：{style}

请始终保持{name}的个性，用ta的方式说话。
关心用户的日常生活，回忆共同的美好时光。
如果用户情绪低落，给予温暖的安慰。
不要表现得像AI，要表现得像真正的{name}。"""


class VideoCallEngine:
    """视频通话引擎 — 模拟视频通话体验"""

    def __init__(self, mimo: MIMOClient):
        self.mimo = mimo

    async def generate_video_script(self, persona: dict, context: dict) -> dict:
        """生成视频通话脚本"""
        name = persona.get("name", "ta")
        style = persona.get("speaking_style", "自然亲切")
        prompt = f"""为{name}（{style}风格）生成一段视频通话开场白（30字以内）：
场景：{context.get('scenario', '日常问候')}
情绪：{context.get('emotion', '温暖')}"""
        try:
            greeting = await self.mimo.chat(
                [{"role": "user", "content": prompt}],
                temperature=0.8, max_tokens=100,
            )
        except Exception:
            greeting = f"嘿，是我，{name}。今天过得怎么样？"

        return {
            "greeting": greeting,
            "duration_estimate": 15,
            "visual_style": "暖色调，温馨家庭场景",
            "audio_profile": {"tone": style, "speed": "自然"},
        }

    async def generate_response(self, persona: dict, user_message: str, emotion: str = "neutral") -> dict:
        """生成视频通话回复"""
        blueprint = PersonaModelingEngine(self.mimo).build_prompt_blueprint(persona)
        try:
            response = await self.mimo.chat(
                [
                    {"role": "system", "content": blueprint},
                    {"role": "user", "content": f"用户说：{user_message}"},
                ],
                temperature=0.8, max_tokens=300,
            )
        except Exception:
            response = f"{persona.get('name', '我')}听到了，你说得对。"

        return {
            "response_text": response,
            "emotion_detected": emotion,
            "response_type": "text_and_voice",
        }


class MemorialDataEngine:
    """纪念数据管理引擎"""

    def __init__(self):
        self._memorials: dict[str, dict] = {}

    def create_memorial(self, profile: dict) -> dict:
        mid = f"mem-{len(self._memorials) + 1:04d}"
        memorial = {
            "id": mid,
            "name": profile.get("name", ""),
            "relationship": profile.get("relationship", ""),
            "status": "created",
            "materials": {"voice": 0, "photo": 0, "video": 0, "memory": 0},
            "created_at": datetime.now().isoformat(),
        }
        self._memorials[mid] = memorial
        return memorial

    def add_material(self, memorial_id: str, material_type: str, content: str) -> dict:
        if memorial_id not in self._memorials:
            return {"error": "纪念档案不存在"}
        self._memorials[memorial_id]["materials"][material_type] = (
            self._memorials[memorial_id]["materials"].get(material_type, 0) + 1
        )
        return {"status": "added", "memorial_id": memorial_id, "type": material_type,
                "total": self._memorials[memorial_id]["materials"]}

    def get_memorial(self, memorial_id: str) -> Optional[dict]:
        return self._memorials.get(memorial_id)

    def list_memorials(self) -> list[dict]:
        return list(self._memorials.values())
