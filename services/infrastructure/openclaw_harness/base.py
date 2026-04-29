"""Harness base class — the abstract layer all medical Harnesses extend.

Harness = Tool Chain + Information Format + Context Management
        + Failure Recovery + Result Validation

Core philosophy: The model is swappable; the Harness is proprietary.
A well-designed Harness outperforms a better model with a poor Harness.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class HarnessStatus(str, Enum):
    """Execution status of a Harness run."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    RECOVERED = "recovered"


@dataclass
class HarnessMetrics:
    """Metrics collected during Harness execution."""

    execution_time_ms: float = 0.0
    tools_called: int = 0
    tools_succeeded: int = 0
    context_tokens_used: int = 0
    recovery_attempts: int = 0
    validation_score: float = 0.0


@dataclass
class HarnessResult:
    """Structured result from a Harness execution.

    Attributes:
        output: The validated output data from the Harness.
        harness_name: Name of the Harness that produced this result.
        status: Overall execution status.
        metrics: Performance and reliability metrics.
        metadata: Additional context-specific metadata.
    """

    output: Any = None
    harness_name: str = ""
    status: HarnessStatus = HarnessStatus.SUCCESS
    metrics: HarnessMetrics = field(default_factory=HarnessMetrics)
    metadata: dict[str, Any] = field(default_factory=dict)


class ToolBase(ABC):
    """Abstract base class for tools usable within a Harness.

    Tools are the atomic units of action within a Harness. Each tool
    receives the current context and results from previously executed
    tools, enabling sequential dependency chains.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this tool."""
        ...

    @property
    def description(self) -> str:
        """Human-readable description of what this tool does."""
        return ""

    @abstractmethod
    def execute(
        self,
        context: dict[str, Any],
        prior_results: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute the tool with the given context and prior results.

        Args:
            context: The current Harness context (built by ContextManager).
            prior_results: Results from tools executed earlier in the chain.

        Returns:
            A dict containing this tool's output data.
        """
        ...


class ToolExecutionError(Exception):
    """Raised when a tool fails during execution."""

    def __init__(self, tool_name: str, message: str, recoverable: bool = True):
        self.tool_name = tool_name
        self.recoverable = recoverable
        super().__init__(f"Tool '{tool_name}' failed: {message}")


class ModelProviderBase(ABC):
    """Abstract base for model providers (pluggable backends).

    The model is the most replaceable component of the Harness.
    This interface allows swapping between Mimo, GPT-4, Claude,
    or any other LLM provider without changing the Harness logic.
    """

    @abstractmethod
    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate a response from the model.

        Args:
            prompt: The formatted prompt string.
            **kwargs: Provider-specific parameters.

        Returns:
            The model's text response.
        """
        ...


class BaseHarness(ABC):
    """Base class for all medical Harnesses.

    A Harness encapsulates:
      1. Tool chain — ordered sequence of tools to call
      2. Information format — how context is structured and compressed
      3. Context management — building, compressing, and passing context
      4. Failure recovery — automatic escalation on failure
      5. Result validation — domain-specific output verification

    The core insight: models are interchangeable, Harnesses are proprietary.
    Investing in Harness design yields more returns than model upgrades.

    Attributes:
        name: Unique name for this Harness instance.
        model_provider: The LLM backend (default: "mimo").
        tools: Ordered list of ToolBase instances to execute.
        context_config: Configuration for the ContextManager.
        recovery_strategy: Strategy for handling failures.
    """

    def __init__(
        self,
        name: str,
        model_provider: str | ModelProviderBase = "mimo",
        tools: list[ToolBase] | None = None,
        context_config: Any | None = None,
        recovery_strategy: Any = None,
    ) -> None:
        from .context import ContextManager, ContextConfig
        from .recovery import FailureRecovery, RecoveryStrategy

        self.name = name
        self._model_provider_str = (
            model_provider if isinstance(model_provider, str) else "custom"
        )
        self._model_provider = model_provider
        self.tools: list[ToolBase] = tools or []
        self.context = ContextManager(context_config or ContextConfig())
        self.recovery = FailureRecovery(
            strategy=recovery_strategy or RecoveryStrategy.ESCALATE
        )
        from .validator import ResultValidator
        self.validator = ResultValidator()

    def execute(self, input_data: dict[str, Any]) -> HarnessResult:
        """Execute the full Harness pipeline.

        Pipeline stages:
          1. Context build — structure input into Harness context
          2. Tool chain — execute tools in order with dependency passing
          3. Model reasoning — generate insights from tool results
          4. Validation — verify output meets domain standards
          5. Recovery — handle failures with escalation if needed

        Args:
            input_data: Raw input dict (symptoms, patient data, etc.)

        Returns:
            HarnessResult with validated output and execution metrics.
        """
        start_time = time.monotonic()
        metrics = HarnessMetrics()

        # Stage 1: Context construction
        ctx = self.context.build(input_data)

        # Stage 2: Tool chain execution
        tool_results = self._chain_tools(ctx, metrics)

        # Stage 3: Model reasoning (Harness-wrapped)
        reasoning = self._reason(ctx, tool_results)

        # Stage 4: Result validation
        validated = self.validator.validate(reasoning, domain=self._domain())
        metrics.validation_score = validated.score

        # Stage 5: Failure recovery
        if not validated.passed:
            metrics.recovery_attempts += 1
            recovery_result = self.recovery.recover(ctx, validated, tool_results)
            if recovery_result.recovered:
                validated = recovery_result.validation
                status = HarnessStatus.RECOVERED
            else:
                status = HarnessStatus.FAILED
        else:
            status = HarnessStatus.SUCCESS

        metrics.execution_time_ms = (time.monotonic() - start_time) * 1000

        return HarnessResult(
            output=validated,
            harness_name=self.name,
            status=status,
            metrics=metrics,
            metadata={"domain": self._domain(), "model": self._model_provider_str},
        )

    def add_tool(self, tool: ToolBase) -> None:
        """Register a tool to this Harness's tool chain."""
        self.tools.append(tool)

    def _chain_tools(
        self,
        context: dict[str, Any],
        metrics: HarnessMetrics,
    ) -> dict[str, Any]:
        """Execute the tool chain sequentially, passing prior results forward."""
        results: dict[str, Any] = {}
        for tool in self.tools:
            metrics.tools_called += 1
            try:
                result = tool.execute(context, results)
                results[tool.name] = result
                metrics.tools_succeeded += 1
            except ToolExecutionError as exc:
                if not exc.recoverable:
                    raise
                results[tool.name] = {"error": str(exc), "recoverable": True}
        return results

    def _reason(
        self,
        context: dict[str, Any],
        tool_results: dict[str, Any],
    ) -> str:
        """Perform model reasoning with Harness-structured prompt."""
        prompt = self._build_prompt(context, tool_results)
        if isinstance(self._model_provider, str):
            return self._default_reasoning(prompt)
        return self._model_provider.generate(prompt)

    def _default_reasoning(self, prompt: str) -> str:
        """Default reasoning stub when no real model provider is configured."""
        return f"[Harness:{self.name}] Model reasoning placeholder. Prompt length: {len(prompt)}"

    @abstractmethod
    def _build_prompt(
        self,
        context: dict[str, Any],
        tool_results: dict[str, Any],
    ) -> str:
        """Build a domain-specific prompt from context and tool results."""
        ...

    @abstractmethod
    def _domain(self) -> str:
        """Return the domain identifier for this Harness."""
        ...
