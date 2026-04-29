"""Context Manager — builds, compresses, and transfers Harness context.

The context manager is a critical Harness component. It determines
HOW information flows through the Harness pipeline, directly impacting
model reasoning quality.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
from datetime import datetime, timezone


class CompressionStrategy(str, Enum):
    """Strategy for compressing context when it exceeds token limits."""

    TRUNCATE = "truncate"
    SUMMARIZE = "summarize"
    HIERARCHICAL = "hierarchical"
    MEDICAL_PRIORITIZED = "medical_prioritized"


@dataclass
class ContextConfig:
    """Configuration for the ContextManager.

    Attributes:
        max_tokens: Maximum context tokens before compression.
        compression_strategy: How to handle context overflow.
        include_metadata: Whether to include Harness metadata.
        patient_history_depth: Historical encounters to include.
        retain_critical_flags: Always keep flagged items (allergies, alerts).
    """

    max_tokens: int = 8192
    compression_strategy: CompressionStrategy = CompressionStrategy.MEDICAL_PRIORITIZED
    include_metadata: bool = True
    patient_history_depth: int = 5
    retain_critical_flags: bool = True


class ContextManager:
    """Manages context lifecycle within a Harness.

    Responsibilities:
      - Build structured context from raw input data
      - Compress context when approaching token limits
      - Maintain critical information (allergies, drug interactions)
      - Pass context between Harness stages with continuity
    """

    def __init__(self, config: ContextConfig | None = None) -> None:
        self.config = config or ContextConfig()
        self._history: list[dict[str, Any]] = []
        self._critical_items: list[dict[str, Any]] = []

    def build(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Build a structured Harness context from raw input.

        Args:
            input_data: Raw input (symptoms, patient data, etc.)

        Returns:
            Structured context dict ready for tool chain and reasoning.
        """
        if self.config.retain_critical_flags:
            self._extract_critical_items(input_data)

        context: dict[str, Any] = {
            "input": input_data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "history": self._history[-self.config.patient_history_depth :],
            "critical_items": list(self._critical_items),
            "stage": "initial",
        }

        if self.config.include_metadata:
            context["metadata"] = {
                "compression_strategy": self.config.compression_strategy.value,
                "max_tokens": self.config.max_tokens,
            }

        return context

    def compress(self, context: dict[str, Any]) -> dict[str, Any]:
        """Compress context to fit within token limits.

        Args:
            context: The full context dict.

        Returns:
            Compressed context dict.
        """
        estimated_tokens = self._estimate_tokens(context)
        if estimated_tokens <= self.config.max_tokens:
            return context

        strategy = self.config.compression_strategy
        if strategy == CompressionStrategy.TRUNCATE:
            return self._compress_truncate(context)
        elif strategy == CompressionStrategy.SUMMARIZE:
            return self._compress_summarize(context)
        elif strategy == CompressionStrategy.HIERARCHICAL:
            return self._compress_hierarchical(context)
        elif strategy == CompressionStrategy.MEDICAL_PRIORITIZED:
            return self._compress_medical_prioritized(context)
        return context

    def update_history(self, context: dict[str, Any], result: Any) -> None:
        """Add an execution result to the context history."""
        self._history.append({
            "stage": context.get("stage", "unknown"),
            "result_summary": str(result)[:200],
        })

    def _extract_critical_items(self, input_data: dict[str, Any]) -> None:
        """Extract clinically critical items that must never be compressed."""
        critical_keys = {"allergies", "drug_interactions", "alerts", "critical_flags"}
        for key in critical_keys:
            if key in input_data and input_data[key]:
                self._critical_items.append({
                    "type": key,
                    "value": input_data[key],
                    "priority": "critical",
                })

    def _compress_truncate(self, context: dict[str, Any]) -> dict[str, Any]:
        compressed = dict(context)
        if "history" in compressed:
            compressed["history"] = compressed["history"][-2:]
        compressed["_compressed"] = True
        return compressed

    def _compress_summarize(self, context: dict[str, Any]) -> dict[str, Any]:
        compressed = dict(context)
        if "history" in compressed and compressed["history"]:
            compressed["history_summary"] = f"{len(compressed['history'])} prior stages"
            compressed["history"] = compressed["history"][-1:]
        compressed["_compressed"] = True
        return compressed

    def _compress_hierarchical(self, context: dict[str, Any]) -> dict[str, Any]:
        compressed = dict(context)
        for key in list(compressed.keys()):
            if isinstance(compressed[key], dict) and key not in ("input", "critical_items"):
                compressed[key] = {k: type(v).__name__ for k, v in compressed[key].items()}
        compressed["_compressed"] = True
        return compressed

    def _compress_medical_prioritized(self, context: dict[str, Any]) -> dict[str, Any]:
        return {
            "input": context.get("input", {}),
            "critical_items": context.get("critical_items", []),
            "history": context.get("history", [])[-2:],
            "stage": context.get("stage", "initial"),
            "_compressed": True,
            "_strategy": "medical_prioritized",
        }

    @staticmethod
    def _estimate_tokens(context: dict[str, Any]) -> int:
        text = json.dumps(context, default=str)
        return len(text) // 4
