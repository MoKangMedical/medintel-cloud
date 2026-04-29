"""
结构化讨论引擎 — 整合自 DrugMind
"""

import logging
import uuid
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional

from ..digital_twin.engine import DigitalTwinEngine, TwinResponse

logger = logging.getLogger(__name__)


@dataclass
class DiscussionMessage:
    message_id: str
    session_id: str
    twin_id: str
    name: str
    role: str
    emoji: str
    content: str
    message_type: str = "discussion"
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class DiscussionSession:
    session_id: str
    topic: str
    participants: list[str]
    messages: list[DiscussionMessage] = field(default_factory=list)
    status: str = "active"
    created_at: str = ""
    summary: str = ""
    decision: str = ""


class DiscussionEngine:
    def __init__(self, twin_engine: DigitalTwinEngine):
        self.twin = twin_engine
        self.sessions: dict[str, DiscussionSession] = {}

    def create_discussion(self, topic: str, participant_ids: list[str],
                          context: str = "") -> DiscussionSession:
        session_id = f"disc_{uuid.uuid4().hex[:8]}"
        session = DiscussionSession(session_id=session_id, topic=topic,
                                    participants=participant_ids,
                                    created_at=datetime.now().isoformat())
        self.sessions[session_id] = session
        return session

    def run_round_robin(self, session_id: str, context: str = "",
                        max_rounds: int = 2) -> list[DiscussionMessage]:
        session = self.sessions.get(session_id)
        if not session:
            return []

        all_messages = []
        history = ""
        for round_num in range(max_rounds):
            for twin_id in session.participants:
                discussion_context = f"## 议题\n{session.topic}\n\n"
                if context:
                    discussion_context += f"## 背景\n{context}\n\n"
                if history:
                    discussion_context += f"## 之前发言\n{history}\n\n"

                response = self.twin.ask_twin(
                    twin_id=twin_id,
                    question=f"请就以下议题发表专业意见：\n{session.topic}",
                    context=discussion_context,
                )
                msg = DiscussionMessage(
                    message_id=uuid.uuid4().hex[:8], session_id=session_id,
                    twin_id=twin_id, name=response.name, role=response.role,
                    emoji=response.emoji, content=response.message,
                )
                session.messages.append(msg)
                all_messages.append(msg)
                history += f"\n{response.emoji} **{response.name}** ({response.role}):\n{response.message}\n"

        session.status = "completed"
        return all_messages

    def run_debate(self, session_id: str, question: str, context: str = "") -> dict:
        session = self.sessions.get(session_id)
        if not session or len(session.participants) < 2:
            return {"error": "辩论至少需要2个参与者"}

        mid = len(session.participants) // 2
        pro_side, con_side = session.participants[:mid], session.participants[mid:]
        debate = {"question": question, "pro_side": [], "con_side": []}

        for tid in pro_side:
            r = self.twin.ask_twin(tid, f"请支持以下观点：{question}", context)
            debate["pro_side"].append(asdict(r))
        for tid in con_side:
            r = self.twin.ask_twin(tid, f"请反对以下观点：{question}", context)
            debate["con_side"].append(asdict(r))
        return debate

    def summarize_discussion(self, session_id: str) -> str:
        session = self.sessions.get(session_id)
        if not session or not session.messages:
            return "无讨论记录"
        summary = f"# 讨论摘要: {session.topic}\n\n参与者: {len(session.participants)}位\n消息数: {len(session.messages)}\n\n"
        role_opinions = {}
        for msg in session.messages:
            role_opinions.setdefault(msg.role, []).append(msg.content[:200])
        for role, opinions in role_opinions.items():
            summary += f"### {role}\n"
            for op in opinions:
                summary += f"- {op}\n"
        session.summary = summary
        return summary

    def get_session_messages(self, session_id: str, limit: int = 50) -> list[dict]:
        session = self.sessions.get(session_id)
        if not session:
            return []
        return [{"message_id": m.message_id, "emoji": m.emoji, "name": m.name,
                 "role": m.role, "content": m.content, "timestamp": m.timestamp}
                for m in session.messages[-limit:]]

    def list_sessions(self) -> list[dict]:
        return [{"session_id": s.session_id, "topic": s.topic,
                 "participants": len(s.participants), "messages": len(s.messages),
                 "status": s.status, "created_at": s.created_at} for s in self.sessions.values()]
