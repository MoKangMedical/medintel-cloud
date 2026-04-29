"""
🍐 念念 (Minder) — API 路由

智能语音提醒的核心 API 接口。
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

router = APIRouter()


# ── Health ────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok", service="Minder", version="0.1.0")


# ── 念想模型 ──────────────────────────────────────────────────────────

class ReminderCreate(BaseModel):
    """创建念想请求"""
    content: str = Field(..., min_length=1, description="念想内容（自然语言）")
    voice_input: bool = Field(default=False, description="是否语音输入")
    category: Optional[str] = Field(default=None, description="分类（自动识别或手动）")
    remind_at: Optional[str] = Field(default=None, description="提醒时间（ISO格式）")
    location: Optional[str] = Field(default=None, description="地点提示")


class Reminder(BaseModel):
    """念想"""
    id: str
    content: str
    category: Optional[str] = None
    remind_at: Optional[str] = None
    location: Optional[str] = None
    status: str = "pending"
    created_at: str
    encouragement: Optional[str] = None


class ReminderListResponse(BaseModel):
    reminders: list[Reminder]
    total: int


class NLPProcessRequest(BaseModel):
    """自然语言处理请求"""
    text: str = Field(..., min_length=1)
    context: Optional[dict] = None


class NLPProcessResponse(BaseModel):
    """NLP 处理结果"""
    extracted_time: Optional[str] = None
    extracted_category: Optional[str] = None
    extracted_location: Optional[str] = None
    cleaned_content: str
    confidence: float = 0.0


# ── 念想 CRUD ─────────────────────────────────────────────────────────

# 内存存储（生产环境应使用数据库）
_reminders: dict[str, Reminder] = {}
_counter = 0


@router.post("/reminders", response_model=Reminder, status_code=201)
async def create_reminder(request: ReminderCreate):
    """创建一个新的念想 💝"""
    global _counter
    _counter += 1
    reminder_id = f"minder_{_counter:06d}"

    reminder = Reminder(
        id=reminder_id,
        content=request.content,
        category=request.category,
        remind_at=request.remind_at,
        location=request.location,
        status="pending",
        created_at=datetime.now().isoformat(),
        encouragement="你真棒！继续加油 💪",
    )
    _reminders[reminder_id] = reminder
    return reminder


@router.get("/reminders", response_model=ReminderListResponse)
async def list_reminders(status: Optional[str] = None):
    """列出所有念想 📋"""
    items = list(_reminders.values())
    if status:
        items = [r for r in items if r.status == status]
    return ReminderListResponse(reminders=items, total=len(items))


@router.get("/reminders/{reminder_id}", response_model=Reminder)
async def get_reminder(reminder_id: str):
    """获取单个念想"""
    if reminder_id not in _reminders:
        raise HTTPException(status_code=404, detail="念想不存在")
    return _reminders[reminder_id]


@router.put("/reminders/{reminder_id}/complete", response_model=Reminder)
async def complete_reminder(reminder_id: str):
    """完成念想 ✅"""
    if reminder_id not in _reminders:
        raise HTTPException(status_code=404, detail="念想不存在")
    reminder = _reminders[reminder_id]
    reminder.status = "completed"
    return reminder


@router.delete("/reminders/{reminder_id}")
async def delete_reminder(reminder_id: str):
    """删除念想"""
    if reminder_id not in _reminders:
        raise HTTPException(status_code=404, detail="念想不存在")
    del _reminders[reminder_id]
    return {"deleted": True}


# ── NLP 处理 ──────────────────────────────────────────────────────────

@router.post("/nlp/process", response_model=NLPProcessResponse)
async def process_natural_language(request: NLPProcessRequest):
    """AI 理解自然语言，提取时间、地点、分类"""
    text = request.text

    # 简易 NLP 处理（生产环境应接入 LLM）
    import re

    # 提取时间
    time_patterns = [
        (r"(\d+)分钟后", "minutes"),
        (r"(\d+)小时后", "hours"),
        (r"明天", "tomorrow"),
        (r"后天", "day_after_tomorrow"),
    ]
    extracted_time = None
    for pattern, label in time_patterns:
        match = re.search(pattern, text)
        if match:
            extracted_time = label
            break

    # 提取分类
    category_keywords = {
        "健康": ["吃药", "体检", "运动", "喝水"],
        "工作": ["会议", "报告", "deadline", "邮件"],
        "生活": ["买菜", "做饭", "取快递", "接孩子"],
    }
    extracted_category = None
    for cat, keywords in category_keywords.items():
        if any(kw in text for kw in keywords):
            extracted_category = cat
            break

    # 清理内容
    cleaned = re.sub(r"(明天|后天|下午|上午|\d+分钟后|\d+小时后)", "", text).strip()

    return NLPProcessResponse(
        extracted_time=extracted_time,
        extracted_category=extracted_category,
        extracted_location=None,
        cleaned_content=cleaned or text,
        confidence=0.75,
    )
