"""
🏗️ OpenClaw Harness — 管理 API 路由

提供 Harness 框架的管理接口: 注册、执行、监控、验证。
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Optional
from enum import Enum

router = APIRouter()


# ── Health ────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    registered_harnesses: int = 0


@router.get("/health", response_model=HealthResponse)
async def health():
    from .service import harness_registry
    return HealthResponse(
        status="ok",
        service="OpenClaw-Harness",
        version="0.1.0",
        registered_harnesses=len(harness_registry),
    )


# ── Harness Registration ──────────────────────────────────────────────

class HarnessType(str, Enum):
    DIAGNOSIS = "diagnosis"
    DRUG_DISCOVERY = "drug_discovery"
    HEALTH_MANAGEMENT = "health_management"
    CUSTOM = "custom"


class RegisterHarnessRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128, description="Harness 名称")
    harness_type: HarnessType = Field(default=HarnessType.CUSTOM, description="Harness 类型")
    model_provider: str = Field(default="mimo", description="模型后端")
    description: Optional[str] = None


class HarnessInfo(BaseModel):
    id: str
    name: str
    harness_type: str
    model_provider: str
    description: Optional[str] = None
    tool_count: int = 0
    status: str = "ready"


class HarnessListResponse(BaseModel):
    harnesses: list[HarnessInfo]
    total: int


@router.post("/register", response_model=HarnessInfo, status_code=201)
async def register_harness(request: RegisterHarnessRequest):
    """注册一个新的 Harness 实例。"""
    from .service import register_harness as _register
    return _register(request)


@router.get("/list", response_model=HarnessListResponse)
async def list_harnesses():
    """列出所有已注册的 Harness。"""
    from .service import harness_registry
    infos = [
        HarnessInfo(
            id=h_id,
            name=h.name,
            harness_type=h._domain(),
            model_provider=h._model_provider_str,
            tool_count=len(h.tools),
        )
        for h_id, h in harness_registry.items()
    ]
    return HarnessListResponse(harnesses=infos, total=len(infos))


# ── Execution ─────────────────────────────────────────────────────────

class ExecuteRequest(BaseModel):
    harness_id: str = Field(..., description="要执行的 Harness ID")
    input_data: dict[str, Any] = Field(default_factory=dict, description="输入数据")


class ExecuteResponse(BaseModel):
    harness_id: str
    harness_name: str
    status: str
    output: Any = None
    validation_score: float = 0.0
    execution_time_ms: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


@router.post("/execute", response_model=ExecuteResponse)
async def execute_harness(request: ExecuteRequest):
    """执行一个已注册的 Harness。"""
    from .service import execute_harness as _execute
    return _execute(request)


# ── Validation ────────────────────────────────────────────────────────

class ValidateRequest(BaseModel):
    output: Any = Field(..., description="待验证的输出")
    domain: str = Field(default="general", description="医疗领域")


class ValidateResponse(BaseModel):
    passed: bool
    score: float
    message: str
    findings: list[dict[str, Any]] = Field(default_factory=list)


@router.post("/validate", response_model=ValidateResponse)
async def validate_output(request: ValidateRequest):
    """独立验证 Harness 输出。"""
    from .service import validate_output as _validate
    return _validate(request)


# ── Recovery ──────────────────────────────────────────────────────────

class RecoveryLogResponse(BaseModel):
    harness_id: str
    escalation_events: list[dict[str, Any]] = Field(default_factory=list)
    total_failures: int = 0


@router.get("/recovery/{harness_id}", response_model=RecoveryLogResponse)
async def get_recovery_log(harness_id: str):
    """获取指定 Harness 的失败恢复日志。"""
    from .service import get_recovery_log as _get_log
    return _get_log(harness_id)
