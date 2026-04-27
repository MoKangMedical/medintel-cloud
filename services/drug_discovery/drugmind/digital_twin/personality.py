"""
数字分身人格管理系统 — 整合自 DrugMind
"""

import json
import logging
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional

from .roles import get_role, ROLE_REGISTRY

logger = logging.getLogger(__name__)


@dataclass
class PersonalityProfile:
    role_id: str
    name: str
    avatar_emoji: str
    custom_expertise: list[str] = field(default_factory=list)
    custom_system_prompt: str = ""
    risk_tolerance_override: Optional[float] = None
    innovation_style_override: Optional[float] = None
    knowledge_files: list[str] = field(default_factory=list)
    memory_entries: list[dict] = field(default_factory=list)


class PersonalityManager:
    def __init__(self, profiles_dir: str = "./profiles"):
        self.profiles_dir = Path(profiles_dir)
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self._profiles: dict[str, PersonalityProfile] = {}
        self._load_profiles()

    def create_twin(self, role_id: str, name: str, custom_expertise: Optional[list[str]] = None) -> PersonalityProfile:
        role = get_role(role_id)
        profile = PersonalityProfile(role_id=role_id, name=name, avatar_emoji=role.emoji,
                                     custom_expertise=custom_expertise or [])
        twin_id = f"{role_id}_{name}"
        self._profiles[twin_id] = profile
        self._save_profile(twin_id, profile)
        return profile

    def get_system_prompt(self, twin_id: str) -> str:
        profile = self._profiles.get(twin_id)
        if not profile:
            return "你是一个通用药物研发AI助手。"
        role = get_role(profile.role_id)
        prompt = profile.custom_system_prompt or role.system_prompt
        if profile.custom_expertise:
            prompt += f"\n\n额外专业领域：{', '.join(profile.custom_expertise)}"
        if profile.memory_entries:
            recent = profile.memory_entries[-5:]
            prompt += f"\n\n经验记忆：\n" + "\n".join(f"- {m.get('content', '')[:100]}" for m in recent)
        risk = profile.risk_tolerance_override or role.risk_tolerance
        innovation = profile.innovation_style_override or role.innovation_style
        prompt += f"\n\n人格参数：风险容忍度={risk:.1f}，创新倾向={innovation:.1f}"
        return prompt

    def add_knowledge(self, twin_id: str, file_path: str, content: str):
        profile = self._profiles.get(twin_id)
        if profile:
            profile.knowledge_files.append(file_path)
            profile.memory_entries.append({"type": "knowledge", "source": file_path,
                                            "content": content[:2000], "timestamp": __import__('datetime').datetime.now().isoformat()})
            self._save_profile(twin_id, profile)

    def add_memory(self, twin_id: str, content: str, memory_type: str = "experience"):
        profile = self._profiles.get(twin_id)
        if profile:
            import datetime
            profile.memory_entries.append({"type": memory_type, "content": content,
                                            "timestamp": datetime.datetime.now().isoformat()})
            if len(profile.memory_entries) > 100:
                profile.memory_entries = profile.memory_entries[-100:]
            self._save_profile(twin_id, profile)

    def list_twins(self) -> list[dict]:
        result = []
        for tid, p in self._profiles.items():
            role = get_role(p.role_id)
            result.append({"twin_id": tid, "name": p.name, "role": role.display_name,
                           "emoji": p.avatar_emoji, "memory_count": len(p.memory_entries)})
        return result

    def _save_profile(self, twin_id: str, profile: PersonalityProfile):
        path = self.profiles_dir / f"{twin_id}.json"
        path.write_text(json.dumps(asdict(profile), ensure_ascii=False, indent=2))

    def _load_profiles(self):
        if not self.profiles_dir.exists():
            return
        for path in self.profiles_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text())
                self._profiles[path.stem] = PersonalityProfile(**data)
            except Exception as e:
                logger.warning(f"Load profile failed {path}: {e}")
