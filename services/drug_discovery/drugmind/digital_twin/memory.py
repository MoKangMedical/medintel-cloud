"""
层级记忆系统 — 整合自 DrugMind / Second Me
三层记忆：L0原始数据 → L1结构化知识 → L2高层洞察
"""

import json
import logging
from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    content: str
    memory_type: str  # raw / knowledge / decision / insight
    source: str = ""
    importance: float = 0.5
    timestamp: str = ""
    tags: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class HierarchicalMemory:
    def __init__(self, storage_dir: str = "./memory"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.l0_raw: list[MemoryEntry] = []
        self.l1_structured: list[MemoryEntry] = []
        self.l2_insights: list[MemoryEntry] = []

    def add_raw(self, content: str, source: str = "", tags: list[str] = None):
        self.l0_raw.append(MemoryEntry(content=content, memory_type="raw", source=source,
                                        tags=tags or [], importance=0.3))
        if len(content) > 100:
            lines = [l.strip() for l in content.split("\n") if len(l.strip()) > 30][:5]
            for line in lines:
                self.l1_structured.append(MemoryEntry(content=line, memory_type="knowledge",
                                                       source=source, importance=0.5, tags=tags or []))

    def add_knowledge(self, content: str, source: str = "", importance: float = 0.7):
        self.l1_structured.append(MemoryEntry(content=content, memory_type="knowledge",
                                               source=source, importance=importance))

    def add_insight(self, content: str, tags: list[str] = None):
        self.l2_insights.append(MemoryEntry(content=content, memory_type="insight",
                                             importance=0.9, tags=tags or []))

    def add_decision(self, decision: str, rationale: str, context: str = ""):
        content = f"决策: {decision}\n理由: {rationale}"
        if context:
            content += f"\n背景: {context}"
        self.l1_structured.append(MemoryEntry(content=content, memory_type="decision",
                                               importance=0.8, tags=["decision"]))

    def retrieve(self, query: str = "", memory_type: str = "all", max_entries: int = 10) -> list[MemoryEntry]:
        all_entries = []
        if memory_type in ("all", "insight"):
            all_entries.extend(self.l2_insights)
        if memory_type in ("all", "knowledge"):
            all_entries.extend(self.l1_structured)
        if memory_type in ("all", "raw"):
            all_entries.extend(self.l0_raw)

        if not query:
            all_entries.sort(key=lambda e: e.importance, reverse=True)
            return all_entries[:max_entries]

        query_lower = query.lower()
        scored = []
        for entry in all_entries:
            score = sum(1 for word in query_lower.split() if word in entry.content.lower()) * entry.importance
            if score > 0:
                scored.append((score, entry))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored[:max_entries]]

    def get_context_for_discussion(self, topic: str) -> str:
        relevant = self.retrieve(topic, max_entries=5)
        if not relevant:
            return ""
        parts = ["## 相关记忆和知识\n"]
        for e in relevant:
            parts.append(f"- [{e.memory_type}] {e.content[:200]}")
        return "\n".join(parts)

    def save(self, twin_id: str):
        data = {"l0_raw": [asdict(e) for e in self.l0_raw[-200:]],
                "l1_structured": [asdict(e) for e in self.l1_structured[-200:]],
                "l2_insights": [asdict(e) for e in self.l2_insights]}
        path = self.storage_dir / f"{twin_id}_memory.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def load(self, twin_id: str):
        path = self.storage_dir / f"{twin_id}_memory.json"
        if path.exists():
            data = json.loads(path.read_text())
            self.l0_raw = [MemoryEntry(**e) for e in data.get("l0_raw", [])]
            self.l1_structured = [MemoryEntry(**e) for e in data.get("l1_structured", [])]
            self.l2_insights = [MemoryEntry(**e) for e in data.get("l2_insights", [])]
