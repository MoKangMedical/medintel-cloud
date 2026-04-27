"""
🧪 念念 (Minder) — 单元测试

测试 Minder 智能语音提醒服务的 API 接口。
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.cognitive_commerce.minder.api import (
    ReminderCreate,
    Reminder,
    NLPProcessRequest,
    NLPProcessResponse,
)


class TestReminderModel:
    def test_create_reminder(self):
        """测试创建念想模型"""
        r = ReminderCreate(content="明天下午3点开会")
        assert r.content == "明天下午3点开会"
        assert r.voice_input is False

    def test_reminder_defaults(self):
        """测试念想默认值"""
        r = Reminder(
            id="test_001",
            content="测试",
            created_at="2024-01-01T00:00:00",
        )
        assert r.status == "pending"
        assert r.category is None


class TestNLPProcess:
    def test_nlp_request(self):
        """测试 NLP 请求模型"""
        req = NLPProcessRequest(text="明天下午买菜")
        assert req.text == "明天下午买菜"
