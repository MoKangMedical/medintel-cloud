"""
🏗️ OpenClaw Harness — 服务层

Harness 注册、执行、验证的业务逻辑实现。
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from .base import BaseHarness, HarnessResult, ToolBase, ModelProviderBase
from .context import ContextManager, ContextConfig
from .recovery import FailureRecovery, RecoveryStrategy, EscalationEvent
from .validator import ResultValidator, ValidationResult

# ── Global Harness Registry ──────────────────────────────────────────

harness_registry: dict[str, BaseHarness] = {}


# ── Simple Harness Implementations for Registration ──────────────────

class _GenericHarness(BaseHarness):
    """通用 Harness，用于注册自定义 Harness 实例。"""

    def __init__(
        self,
        name: str,
        domain: str = "general",
        model_provider: str | ModelProviderBase = "mimo",
        tools: list[ToolBase] | None = None,
    ) -> None:
        self._domain_name = domain
        super().__init__(name=name, model_provider=model_provider, tools=tools)

    def _build_prompt(self, context: dict[str, Any], tool_results: dict[str, Any]) -> str:
        return f"Domain: {self._domain_name}\nContext: {context}\nTools: {tool_results}"

    def _domain(self) -> str:
        return self._domain_name


# ── Service Functions ─────────────────────────────────────────────────

def register_harness(request: Any) -> Any:
    """注册一个新的 Harness 实例。"""
    from .api import HarnessInfo, HarnessType, RegisterHarnessRequest

    harness_id = str(uuid.uuid4())[:8]
    harness = _GenericHarness(
        name=request.name,
        domain=request.harness_type.value,
        model_provider=request.model_provider,
    )
    harness_registry[harness_id] = harness

    return HarnessInfo(
        id=harness_id,
        name=harness.name,
        harness_type=harness._domain(),
        model_provider=harness._model_provider_str,
        description=request.description,
        tool_count=len(harness.tools),
        status="ready",
    )


def execute_harness(request: Any) -> Any:
    """执行一个已注册的 Harness。"""
    from .api import ExecuteRequest, ExecuteResponse

    harness = harness_registry.get(request.harness_id)
    if harness is None:
        raise KeyError(f"Harness '{request.harness_id}' not found")

    result: HarnessResult = harness.execute(request.input_data)

    return ExecuteResponse(
        harness_id=request.harness_id,
        harness_name=result.harness_name,
        status=result.status.value,
        output=result.output if hasattr(result.output, "__dict__") else str(result.output),
        validation_score=result.metrics.validation_score,
        execution_time_ms=result.metrics.execution_time_ms,
        metadata=result.metadata,
    )


def validate_output(request: Any) -> Any:
    """独立验证 Harness 输出。"""
    from .api import ValidateRequest, ValidateResponse

    validator = ResultValidator()
    result: ValidationResult = validator.validate(request.output, domain=request.domain)

    findings_list = [
        {
            "severity": f.severity.value,
            "field": f.field,
            "message": f.message,
            "suggestion": f.suggestion,
        }
        for f in result.findings
    ]

    return ValidateResponse(
        passed=result.passed,
        score=result.score,
        message=result.message,
        findings=findings_list,
    )


def get_recovery_log(harness_id: str) -> Any:
    """获取指定 Harness 的失败恢复日志。"""
    from .api import RecoveryLogResponse

    harness = harness_registry.get(harness_id)
    if harness is None:
        raise KeyError(f"Harness '{harness_id}' not found")

    events: list[EscalationEvent] = harness.recovery.escalation_log
    events_list = [
        {
            "level": e.level.value,
            "source": e.source,
            "reason": e.reason,
            "resolution": e.resolution,
            "context_snapshot": e.context_snapshot,
        }
        for e in events
    ]

    return RecoveryLogResponse(
        harness_id=harness_id,
        escalation_events=events_list,
        total_failures=len(events),
    )


# ── Service App Entry Point ───────────────────────────────────────────

def create_app():
    """创建 FastAPI 应用。"""
    import uvicorn
    from fastapi import FastAPI

    app = FastAPI(
        title="OpenClaw Harness",
        version="0.1.0",
        description="🏗️ MedIntel Cloud — 统一编排框架管理接口",
    )

    from .api import router
    app.include_router(router, prefix="/harness")

    return app


if __name__ == "__main__":
    import uvicorn
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8100)
