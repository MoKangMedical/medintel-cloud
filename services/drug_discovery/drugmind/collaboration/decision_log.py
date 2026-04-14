"""
决策追踪模块 — 整合自 DrugMind
"""

import json
import logging
from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class DecisionRecord:
    decision_id: str
    topic: str
    decision: str  # GO / NO-GO / CONDITIONAL
    rationale: str
    participants: list[str]
    opinions: list[dict]
    dissenting: list[str]
    conditions: list[str]
    timestamp: str = ""
    session_id: str = ""


class DecisionLogger:
    def __init__(self, log_dir: str = "./drugmind_data/decisions"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.records: list[DecisionRecord] = []

    def log_decision(self, topic: str, decision: str, rationale: str,
                     participants: list[str], opinions: list[dict],
                     dissenting: list[str] = None, conditions: list[str] = None,
                     session_id: str = "") -> DecisionRecord:
        record = DecisionRecord(
            decision_id=f"dec_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            topic=topic, decision=decision, rationale=rationale,
            participants=participants, opinions=opinions,
            dissenting=dissenting or [], conditions=conditions or [],
            timestamp=datetime.now().isoformat(), session_id=session_id,
        )
        self.records.append(record)
        path = self.log_dir / f"{record.decision_id}.json"
        path.write_text(json.dumps(asdict(record), ensure_ascii=False, indent=2))
        return record

    def get_decision_history(self, topic_filter: str = "") -> list[dict]:
        records = self.records
        if topic_filter:
            records = [r for r in records if topic_filter.lower() in r.topic.lower()]
        return [asdict(r) for r in records]
