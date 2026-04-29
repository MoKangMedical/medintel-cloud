"""
DrugMind × Second Me 集成层 — 整合自 DrugMind
"""

import json
import logging
from dataclasses import dataclass, asdict
from typing import Optional

from ..digital_twin.roles import get_role

logger = logging.getLogger(__name__)

SECOND_ME_API = "app.secondme.io"
SECOND_ME_REGISTRY = "https://app.secondme.io"


@dataclass
class SecondMeInstance:
    instance_id: str
    name: str
    role: str
    description: str = ""
    public_url: str = ""
    status: str = "created"


class SecondMeIntegration:
    """Second Me集成层（云端/本地双模式）"""

    def __init__(self, mode: str = "cloud", local_url: str = "http://localhost:8002"):
        self.mode = mode
        self.local_url = local_url
        self.instances: dict[str, SecondMeInstance] = {}
        self._conversation_history: dict[str, list] = {}

    def create_pharma_twin(self, name: str, role: str, expertise: list[str],
                           knowledge: list[str] = None, personality: str = "balanced") -> dict:
        training_data = self._build_training_prompt(name, role, expertise, knowledge, personality)
        instance_id = f"{role}_{name}".lower().replace(" ", "_")
        instance = SecondMeInstance(instance_id=instance_id, name=name, role=role,
                                    description=f"{name}的药物研发数字分身 — {role}")
        self.instances[instance_id] = instance
        self._conversation_history[instance_id] = [{"role": "system", "content": training_data}]
        return {"instance_id": instance_id, "name": name, "role": role,
                "status": "ready", "mode": self.mode}

    def chat(self, instance_id: str, message: str) -> dict:
        if instance_id not in self.instances:
            return {"error": f"实例 {instance_id} 不存在"}
        instance = self.instances[instance_id]
        self._conversation_history.setdefault(instance_id, []).append({"role": "user", "content": message})

        if self.mode == "cloud":
            response = self._chat_cloud(instance_id, message)
        else:
            response = self._chat_local(instance_id, message)

        self._conversation_history[instance_id].append({"role": "assistant", "content": response})
        return {"instance_id": instance_id, "name": instance.name, "role": instance.role, "message": response}

    def _chat_cloud(self, instance_id: str, message: str) -> str:
        import http.client
        try:
            history = self._conversation_history.get(instance_id, [])
            conn = http.client.HTTPSConnection(SECOND_ME_API)
            data = {"messages": history[-10:], "temperature": 0.5, "max_tokens": 2000, "stream": False}
            conn.request("POST", f"/api/chat/{instance_id}",
                         body=json.dumps(data), headers={"Content-Type": "application/json"})
            resp = conn.getresponse()
            body = resp.read().decode()
            if resp.status == 200:
                result = json.loads(body)
                return result.get("choices", [{}])[0].get("message", {}).get("content", body)
            return self._local_fallback(instance_id, message)
        except Exception as e:
            return self._local_fallback(instance_id, message)

    def _chat_local(self, instance_id: str, message: str) -> str:
        try:
            import httpx
            history = self._conversation_history.get(instance_id, [])
            resp = httpx.post(f"{self.local_url}/api/chat/{instance_id}",
                              json={"messages": history[-10:], "temperature": 0.5},
                              timeout=60)
            if resp.status_code == 200:
                return resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            return self._local_fallback(instance_id, message)
        except Exception:
            return self._local_fallback(instance_id, message)

    def _local_fallback(self, instance_id: str, message: str) -> str:
        try:
            from core.utils.mimo_client import mimo_chat
            history = self._conversation_history.get(instance_id, [])
            return mimo_chat(messages=history[-10:], temperature=0.5)
        except Exception as e:
            return f"[推理失败: {e}]"

    def _build_training_prompt(self, name, role, expertise, knowledge, personality) -> str:
        try:
            role_config = get_role(role)
            system_prompt = role_config.system_prompt
        except Exception:
            system_prompt = f"你是{name}，一位{role}。"
        return f"""{system_prompt}

你是{name}，一位{role}。

## 专业领域
{chr(10).join(f'- {e}' for e in expertise)}

## 性格
风险容忍度: {'保守' if personality == 'cautious' else '激进' if personality == 'aggressive' else '平衡'}

## 知识库
{chr(10).join(f'- {k}' for k in (knowledge or []))}
"""

    def list_instances(self) -> list[dict]:
        return [{"instance_id": i.instance_id, "name": i.name, "role": i.role,
                 "status": i.status} for i in self.instances.values()]

    def export_for_second_me(self, instance_id: str) -> dict:
        inst = self.instances.get(instance_id)
        if not inst:
            return {"error": "实例不存在"}
        history = self._conversation_history.get(instance_id, [])
        return {"name": inst.name, "description": inst.description,
                "system_prompt": history[0]["content"] if history else "",
                "training_messages": history[1:] if len(history) > 1 else [],
                "metadata": {"domain": "drug_discovery", "role": inst.role, "platform": "DrugMind"}}
