"""
共识形成模块 — 整合自 DrugMind
"""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ConsensusResult:
    topic: str
    final_decision: str
    vote_distribution: dict
    confidence: float
    dissenting_opinions: list[str]


class ConsensusEngine:
    def vote(self, topic: str, options: list[str], votes: dict[str, str],
             weights: dict[str, float] = None) -> ConsensusResult:
        distribution = {opt: 0 for opt in options}
        for twin_id, vote in votes.items():
            w = weights.get(twin_id, 1.0) if weights else 1.0
            distribution[vote] = distribution.get(vote, 0) + w

        winner = max(distribution, key=distribution.get)
        total = sum(distribution.values())
        confidence = distribution[winner] / total if total > 0 else 0
        dissenting = [f"{tid}: 选择了 {vote}" for tid, vote in votes.items() if vote != winner]

        return ConsensusResult(topic=topic, final_decision=winner,
                               vote_distribution=distribution,
                               confidence=round(confidence, 3),
                               dissenting_opinions=dissenting)
