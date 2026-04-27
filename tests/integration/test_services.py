"""
🧪 集成测试 — Harness + Minder

测试 Harness 框架与各服务的集成。
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.mark.asyncio
async def test_harness_api_import():
    """测试 Harness API 模块可导入"""
    from services.infrastructure.openclaw_harness.api import router
    assert router is not None


@pytest.mark.asyncio
async def test_minder_api_import():
    """测试 Minder API 模块可导入"""
    from services.cognitive_commerce.minder.api import router
    assert router is not None


@pytest.mark.asyncio
async def test_harness_register_and_execute():
    """测试 Harness 注册和执行流程"""
    from services.infrastructure.openclaw_harness.service import (
        harness_registry,
        register_harness,
        execute_harness,
    )
    from services.infrastructure.openclaw_harness.api import (
        RegisterHarnessRequest,
        ExecuteRequest,
        HarnessType,
    )

    # 清空注册表
    harness_registry.clear()

    # 注册
    req = RegisterHarnessRequest(
        name="test-harness",
        harness_type=HarnessType.DIAGNOSIS,
    )
    info = register_harness(req)
    assert info.name == "test-harness"
    assert info.id in harness_registry

    # 执行
    exec_req = ExecuteRequest(
        harness_id=info.id,
        input_data={"symptoms": ["fever"]},
    )
    result = execute_harness(exec_req)
    assert result.harness_name == "test-harness"
    assert result.status in ("success", "recovered", "failed")


@pytest.mark.asyncio
async def test_validate_output():
    """测试独立验证接口"""
    from services.infrastructure.openclaw_harness.service import validate_output
    from services.infrastructure.openclaw_harness.api import ValidateRequest

    req = ValidateRequest(
        output={"primary_diagnosis": "flu", "differential_list": ["cold"], "confidence": 0.8},
        domain="diagnosis",
    )
    result = validate_output(req)
    assert isinstance(result.passed, bool)
    assert 0.0 <= result.score <= 1.0
