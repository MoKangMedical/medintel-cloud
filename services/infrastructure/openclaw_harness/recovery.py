"""Failure Recovery — automatic escalation when Harness steps fail.

In medical AI, failure is not an option. The recovery module implements
multi-tier escalation strategies: retry → fallback → human escalation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class RecoveryStrategy(str, Enum):
    """Recovery strategy when a Harness stage fails."""

    RETRY = "retry"
    FALLBACK = "fallback"
    ESCALATE = "escalate"
    DEGRADE_GRACEFULLY = "degrade_gracefully"


class EscalationLevel(str, Enum):
    """Severity levels for escalation."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RecoveryResult:
    """Result of a recovery attempt.

    Attributes:
        recovered: Whether recovery was successful.
        strategy_used: Which recovery strategy was applied.
        validation: Updated validation result after recovery.
        message: Human-readable recovery summary.
        requires_human: Whether human expert review is needed.
    """

    recovered: bool = False
    strategy_used: RecoveryStrategy = RecoveryStrategy.RETRY
    validation: Any = None
    message: str = ""
    requires_human: bool = False


@dataclass
class EscalationEvent:
    """Record of an escalation event for audit trails."""

    level: EscalationLevel = EscalationLevel.MEDIUM
    source: str = ""
    reason: str = ""
    context_snapshot: dict[str, Any] | None = None
    resolution: str = "pending"


class FailureRecovery:
    """Manages failure recovery and escalation within a Harness.

    The recovery system operates on the principle that in medical AI,
    graceful degradation is preferred over silent failure.

    Attributes:
        strategy: Default recovery strategy.
        max_retries: Maximum retry attempts before escalating.
        escalation_threshold: Number of failures before human escalation.
    """

    def __init__(
        self,
        strategy: RecoveryStrategy = RecoveryStrategy.ESCALATE,
        max_retries: int = 2,
        escalation_threshold: int = 3,
    ) -> None:
        self.strategy = strategy
        self.max_retries = max_retries
        self.escalation_threshold = escalation_threshold
        self._escalation_log: list[EscalationEvent] = []
        self._failure_count: int = 0

    def recover(
        self,
        context: dict[str, Any],
        validation_result: Any,
        tool_results: dict[str, Any] | None = None,
    ) -> RecoveryResult:
        """Attempt recovery from a validation or execution failure.

        Args:
            context: The current Harness context.
            validation_result: The failed validation result.
            tool_results: Results from the tool chain.

        Returns:
            RecoveryResult indicating recovery outcome.
        """
        self._failure_count += 1
        severity = self._assess_severity(validation_result)

        event = EscalationEvent(
            level=severity,
            source="validation",
            reason=getattr(validation_result, "message", "Validation failed"),
            context_snapshot=self._safe_context_snapshot(context),
        )

        if severity == EscalationLevel.CRITICAL:
            event.resolution = "escalated_to_human"
            self._escalation_log.append(event)
            return RecoveryResult(
                recovered=False,
                strategy_used=RecoveryStrategy.ESCALATE,
                validation=validation_result,
                message="Critical failure — human expert review required.",
                requires_human=True,
            )

        if severity == EscalationLevel.HIGH:
            degraded = self._degrade_gracefully(validation_result)
            event.resolution = "degraded_gracefully"
            self._escalation_log.append(event)
            return RecoveryResult(
                recovered=True,
                strategy_used=RecoveryStrategy.DEGRADE_GRACEFULLY,
                validation=degraded,
                message="Partial results returned with uncertainty flags.",
                requires_human=False,
            )

        if severity == EscalationLevel.MEDIUM and self._failure_count <= self.max_retries:
            event.resolution = "retry_attempted"
            self._escalation_log.append(event)
            return RecoveryResult(
                recovered=False,
                strategy_used=RecoveryStrategy.RETRY,
                validation=validation_result,
                message=f"Retry attempt {self._failure_count}/{self.max_retries}.",
                requires_human=False,
            )

        event.resolution = "accepted_with_warnings"
        self._escalation_log.append(event)
        return RecoveryResult(
            recovered=True,
            strategy_used=RecoveryStrategy.DEGRADE_GRACEFULLY,
            validation=validation_result,
            message="Accepted with warnings.",
            requires_human=False,
        )

    def _assess_severity(self, validation_result: Any) -> EscalationLevel:
        """Assess failure severity based on validation score."""
        score = getattr(validation_result, "score", 0.5)
        if score < 0.2:
            return EscalationLevel.CRITICAL
        if score < 0.4:
            return EscalationLevel.HIGH
        if score < 0.6:
            return EscalationLevel.MEDIUM
        return EscalationLevel.LOW

    def _degrade_gracefully(self, validation_result: Any) -> Any:
        """Produce degraded result with uncertainty flags."""
        if hasattr(validation_result, "metadata"):
            validation_result.metadata = getattr(validation_result, "metadata", {})
            validation_result.metadata["degraded"] = True
            validation_result.metadata["uncertainty"] = "high"
        return validation_result

    @staticmethod
    def _safe_context_snapshot(context: dict[str, Any]) -> dict[str, Any]:
        return {
            "stage": context.get("stage", "unknown"),
            "input_keys": list(context.get("input", {}).keys()),
            "has_critical_items": bool(context.get("critical_items")),
        }

    @property
    def escalation_log(self) -> list[EscalationEvent]:
        return list(self._escalation_log)

    def reset(self) -> None:
        self._failure_count = 0
