"""
数字分身引擎 — 整合自 DrugMind
构建、管理和调用药物研发数字分身
"""

import logging
from typing import Optional
from dataclasses import dataclass, asdict

from .personality import PersonalityManager, PersonalityProfile
from .memory import HierarchicalMemory
from .roles import get_role, list_roles

logger = logging.getLogger(__name__)


@dataclass
class TwinResponse:
    twin_id: str
    name: str
    role: str
    emoji: str
    message: str
    confidence: float
    reasoning: str


class DigitalTwinEngine:
    """数字分身引擎"""

    def __init__(self, storage_dir: str = "./drugmind_data", use_llm: bool = True):
        self.personality = PersonalityManager(f"{storage_dir}/profiles")
        self.memories: dict[str, HierarchicalMemory] = {}
        self.storage_dir = storage_dir
        self.use_llm = use_llm
        self._llm_fn = None

        if use_llm:
            try:
                from core.utils.mimo_client import mimo_chat
                self._llm_fn = mimo_chat
                logger.info("✅ MIMO LLM connected")
            except Exception as e:
                logger.warning(f"⚠️ LLM not configured, using templates: {e}")
                self.use_llm = False

    def create_twin(self, role_id: str, name: str,
                    custom_expertise: Optional[list[str]] = None) -> dict:
        profile = self.personality.create_twin(role_id=role_id, name=name,
                                               custom_expertise=custom_expertise)
        twin_id = f"{role_id}_{name}"
        self.memories[twin_id] = HierarchicalMemory(f"{self.storage_dir}/memory")
        self.memories[twin_id].load(twin_id)
        role = get_role(role_id)
        return {"twin_id": twin_id, "name": name, "role": role.display_name,
                "emoji": role.emoji, "status": "created"}

    def ask_twin(self, twin_id: str, question: str, context: str = "",
                 temperature: float = 0.4) -> TwinResponse:
        profile_data = self.personality._profiles.get(twin_id)
        if not profile_data:
            return TwinResponse(twin_id=twin_id, name="Unknown", role="Unknown", emoji="❓",
                                message=f"找不到分身 {twin_id}", confidence=0, reasoning="")

        role = get_role(profile_data.role_id)
        system_prompt = self.personality.get_system_prompt(twin_id)

        memory_context = ""
        if twin_id in self.memories:
            memory_context = self.memories[twin_id].get_context_for_discussion(question)

        full_prompt = question
        if context:
            full_prompt += f"\n\n【讨论背景】\n{context}"
        if memory_context:
            full_prompt += f"\n\n【相关经验】\n{memory_context}"

        if self.use_llm and self._llm_fn:
            try:
                message = self._llm_fn(
                    messages=[{"role": "system", "content": system_prompt},
                              {"role": "user", "content": full_prompt}],
                    temperature=temperature,
                )
                if twin_id in self.memories:
                    self.memories[twin_id].add_decision(
                        decision=message[:100], rationale=message, context=question)
                return TwinResponse(twin_id=twin_id, name=profile_data.name,
                                    role=role.display_name, emoji=role.emoji,
                                    message=message, confidence=0.85,
                                    reasoning=f"基于{role.display_name}专业知识和AI推理")
            except Exception as e:
                logger.error(f"LLM call failed: {e}")

        return TwinResponse(twin_id=twin_id, name=profile_data.name,
                            role=role.display_name, emoji=role.emoji,
                            message=self._template_response(profile_data.role_id, question),
                            confidence=0.3, reasoning="模板回复（LLM未连接）")

    def teach_twin(self, twin_id: str, content: str, source: str = ""):
        if twin_id in self.memories:
            self.memories[twin_id].add_knowledge(content, source)
            self.memories[twin_id].save(twin_id)
        self.personality.add_knowledge(twin_id, source, content)

    def get_twin_memory(self, twin_id: str, query: str = "") -> list[dict]:
        if twin_id in self.memories:
            entries = self.memories[twin_id].retrieve(query)
            return [{"content": e.content, "type": e.memory_type, "importance": e.importance} for e in entries]
        return []

    def list_twins(self) -> list[dict]:
        return self.personality.list_twins()

    def _template_response(self, role_id: str, question: str) -> str:
        templates = {
            "medicinal_chemist": "从合成角度，我需要先评估这个分子的合成路线和SA Score。建议先跑retrosynthesis分析。",
            "biologist": "需要更多实验数据支持。建议设计体外活性和选择性实验。",
            "pharmacologist": "需要关注hERG风险和ADMET特性。安全性评估必须先行。",
            "data_scientist": "从数据角度来看，建议先建立QSAR模型预测活性和ADMET。",
            "project_lead": "综合考虑，我建议先明确Go/No-Go标准，再评估各项指标。",
        }
        return templates.get(role_id, "需要更多信息才能给出建议。")
