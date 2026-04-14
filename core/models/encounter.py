"""
Encounter 数据模型
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class EncounterType(str, Enum):
    INPATIENT = "inpatient"
    OUTPATIENT = "outpatient"
    EMERGENCY = "emergency"
    VIRTUAL = "virtual"
    HOME = "home"


class Encounter(BaseModel):
    id: str = Field(..., description="就诊唯一标识")
    patient_id: str
    encounter_type: EncounterType
    department: Optional[str] = None
    chief_complaint: Optional[str] = None
    diagnosis: list[str] = []
    notes: Optional[str] = None
    started_at: datetime = Field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None
    provider_id: Optional[str] = None
