"""
🧪 OpenClaw Harness — 单元测试

测试 Harness 核心组件: base, context, recovery, validator。
"""

import pytest
import sys
from pathlib import Path

# 确保项目路径可导入
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.infrastructure.openclaw_harness.context import (
    ContextManager,
    ContextConfig,
    CompressionStrategy,
)
from services.infrastructure.openclaw_harness.recovery import (
    FailureRecovery,
    RecoveryStrategy,
    EscalationLevel,
)
from services.infrastructure.openclaw_harness.validator import (
    ResultValidator,
    ValidationSeverity,
)
from services.infrastructure.openclaw_harness.base import (
    HarnessStatus,
    HarnessMetrics,
    ToolExecutionError,
)


# ── ContextManager Tests ─────────────────────────────────────────────

class TestContextManager:
    def test_build_basic_context(self):
        """测试基本上下文构建"""
        cm = ContextManager()
        ctx = cm.build({"symptoms": ["fever", "cough"]})
        assert "input" in ctx
        assert ctx["input"]["symptoms"] == ["fever", "cough"]
        assert "timestamp" in ctx
        assert ctx["stage"] == "initial"

    def test_build_extracts_critical_items(self):
        """测试关键项提取"""
        cm = ContextManager()
        ctx = cm.build({"allergies": ["penicillin"], "symptoms": ["rash"]})
        assert len(ctx["critical_items"]) == 1
        assert ctx["critical_items"][0]["type"] == "allergies"

    def test_compression_no_op_when_under_limit(self):
        """测试上下文未超限时不压缩"""
        cm = ContextManager(ContextConfig(max_tokens=100000))
        ctx = cm.build({"data": "small"})
        compressed = cm.compress(ctx)
        assert "_compressed" not in compressed

    def test_medical_prioritized_compression(self):
        """测试医疗优先压缩策略"""
        cm = ContextManager(ContextConfig(
            max_tokens=10,
            compression_strategy=CompressionStrategy.MEDICAL_PRIORITIZED,
        ))
        ctx = cm.build({"allergies": ["penicillin"], "history": [f"item_{i}" for i in range(100)]})
        compressed = cm.compress(ctx)
        assert compressed["_compressed"] is True
        assert "critical_items" in compressed

    def test_truncate_compression(self):
        """测试截断压缩"""
        cm = ContextManager(ContextConfig(
            max_tokens=10,
            compression_strategy=CompressionStrategy.TRUNCATE,
        ))
        ctx = cm.build({"big_data": "x" * 1000})
        compressed = cm.compress(ctx)
        assert compressed["_compressed"] is True

    def test_update_history(self):
        """测试历史更新"""
        cm = ContextManager()
        ctx = cm.build({"test": True})
        cm.update_history(ctx, {"result": "ok"})
        assert len(cm._history) == 1


# ── FailureRecovery Tests ────────────────────────────────────────────

class TestFailureRecovery:
    def test_critical_failure_requires_human(self):
        """测试严重失败需要人工介入"""
        fr = FailureRecovery()

        class FakeValidation:
            score = 0.1
            message = "Critical error"

        result = fr.recover({"stage": "test"}, FakeValidation())
        assert result.recovered is False
        assert result.requires_human is True

    def test_high_severity_degrades_gracefully(self):
        """测试高严重度优雅降级"""
        fr = FailureRecovery()

        class FakeValidation:
            score = 0.3
            message = "High error"
            metadata = {}

        result = fr.recover({"stage": "test"}, FakeValidation())
        assert result.recovered is True
        assert result.requires_human is False

    def test_medium_retries_within_limit(self):
        """测试中等严重度在重试限制内"""
        fr = FailureRecovery(max_retries=3)

        class FakeValidation:
            score = 0.5
            message = "Medium error"

        result = fr.recover({"stage": "test"}, FakeValidation())
        assert result.recovered is False
        assert "Retry" in result.message

    def test_escalation_log(self):
        """测试升级日志"""
        fr = FailureRecovery()

        class FakeValidation:
            score = 0.1
            message = "Test"

        fr.recover({"stage": "test"}, FakeValidation())
        assert len(fr.escalation_log) == 1

    def test_reset(self):
        """测试重置"""
        fr = FailureRecovery()
        fr._failure_count = 5
        fr.reset()
        assert fr._failure_count == 0


# ── ResultValidator Tests ────────────────────────────────────────────

class TestResultValidator:
    def test_valid_general_output(self):
        """测试通用有效输出"""
        v = ResultValidator()
        result = v.validate({"data": "ok"}, domain="general")
        assert result.passed is True
        assert result.score == 1.0

    def test_diagnosis_missing_required_fields(self):
        """测试诊断缺少必要字段"""
        v = ResultValidator()
        result = v.validate({"data": "ok"}, domain="diagnosis")
        assert result.passed is False

    def test_diagnosis_complete(self):
        """测试完整诊断输出"""
        v = ResultValidator()
        output = {
            "primary_diagnosis": "flu",
            "differential_list": ["cold", "covid"],
            "confidence": 0.85,
        }
        result = v.validate(output, domain="diagnosis")
        assert result.passed is True

    def test_dangerous_pattern_detected(self):
        """测试危险模式检测"""
        v = ResultValidator()
        result = v.validate({"recommendation": "stop all medications immediately"})
        assert result.passed is False
        assert any(f.severity == ValidationSeverity.CRITICAL for f in result.findings)

    def test_strict_mode(self):
        """测试严格模式"""
        v = ResultValidator(strict_mode=True)
        # 诊断缺少差分列表 → warning
        output = {
            "primary_diagnosis": "flu",
            "differential_list": ["only_one"],  # < 2 items
            "confidence": 0.85,
        }
        result = v.validate(output, domain="diagnosis")
        assert result.passed is False  # strict mode treats warnings as failures

    def test_confidence_out_of_range(self):
        """测试置信度越界"""
        v = ResultValidator()
        output = {"confidence": 1.5}
        result = v.validate(output)
        assert result.passed is False

    def test_empty_output(self):
        """测试空输出"""
        v = ResultValidator()
        result = v.validate({})
        assert result.passed is False


# ── HarnessMetrics Tests ─────────────────────────────────────────────

class TestHarnessMetrics:
    def test_default_values(self):
        """测试默认值"""
        m = HarnessMetrics()
        assert m.execution_time_ms == 0.0
        assert m.tools_called == 0
        assert m.validation_score == 0.0


# ── ToolExecutionError Tests ─────────────────────────────────────────

class TestToolExecutionError:
    def test_recoverable_error(self):
        """测试可恢复错误"""
        err = ToolExecutionError("my_tool", "connection timeout", recoverable=True)
        assert err.tool_name == "my_tool"
        assert err.recoverable is True
        assert "my_tool" in str(err)

    def test_non_recoverable_error(self):
        """测试不可恢复错误"""
        err = ToolExecutionError("my_tool", "fatal", recoverable=False)
        assert err.recoverable is False
