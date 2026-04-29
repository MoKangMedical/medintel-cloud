"""
Patient 数据模型 — FHIR R4 兼容
"""

from __future__ import annotations
from datetime import date, datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    UNKNOWN = "unknown"


class Patient(BaseModel):
    """FHIR R4 Patient 资源"""
    id: str = Field(..., description="患者唯一标识")
    name: str = Field(..., description="姓名")
    gender: Gender = Field(default=Gender.UNKNOWN)
    birth_date: Optional[date] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    mrn: Optional[str] = Field(None, description="病历号")
    insurance_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        json_schema_extra = {
            "example": {
                "id": "pat-001",
                "name": "张三",
                "gender": "male",
                "birth_date": "1985-03-15",
                "mrn": "MRN20260001",
            }
        }


class PatientSummary(BaseModel):
    """患者摘要 — 跨服务共享"""
    patient: Patient
    active_conditions: list[str] = []
    current_medications: list[str] = []
    recent_labs: dict[str, str] = {}
    risk_score: Optional[float] = Field(None, ge=0, le=1)
    last_encounter: Optional[datetime] = None
