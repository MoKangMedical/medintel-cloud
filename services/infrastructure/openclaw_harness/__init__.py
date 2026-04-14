"""
🏗️ OpenClaw Medical Harness — 统一编排框架

Harness（环境设计）比模型本身更重要。
模型可以替换，流程编排才是护城河。

核心组件:
    - BaseHarness: 抽象 Harness 层，所有医疗 Harness 的基类
    - ContextManager: 上下文构建、压缩与传递
    - FailureRecovery: 多级失败恢复机制
    - ResultValidator: 临床结果验证与安全筛查
"""

__version__ = "0.1.0"
__author__ = "MedIntel Cloud"

from .base import (
    BaseHarness,
    HarnessResult,
    HarnessStatus,
    HarnessMetrics,
    ToolBase,
    ToolExecutionError,
    ModelProviderBase,
)
from .context import ContextManager, ContextConfig, CompressionStrategy
from .recovery import FailureRecovery, RecoveryStrategy, RecoveryResult, EscalationLevel
from .validator import ResultValidator, ValidationResult, ValidationSeverity

__all__ = [
    # Base
    "BaseHarness",
    "HarnessResult",
    "HarnessStatus",
    "HarnessMetrics",
    "ToolBase",
    "ToolExecutionError",
    "ModelProviderBase",
    # Context
    "ContextManager",
    "ContextConfig",
    "CompressionStrategy",
    # Recovery
    "FailureRecovery",
    "RecoveryStrategy",
    "RecoveryResult",
    "EscalationLevel",
    # Validator
    "ResultValidator",
    "ValidationResult",
    "ValidationSeverity",
]
