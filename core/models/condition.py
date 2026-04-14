"""
Condition/Diagnosis 数据模型
"""

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field


class Condition(BaseModel):
    id: str
    patient_id: str
    code: str = Field(..., description="ICD-10/SNOMED编码")
    display: str
    category: Optional[str] = None
    severity: Optional[str] = None
    onset_date: Optional[date] = None
    abatement_date: Optional[date] = None
    status: str = "active"
    recorded_at: datetime = Field(default_factory=datetime.now)


class Diagnosis(Condition):
    """临床诊断 — 带推理链"""
    confidence: Optional[float] = Field(None, ge=0, le=1)
    reasoning: Optional[str] = None
    differentials: list[str] = []
    evidence: list[str] = []
