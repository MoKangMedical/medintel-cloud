"""
Observation 数据模型 — 检验检查结果
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ObservationStatus(str, Enum):
    PRELIMINARY = "preliminary"
    FINAL = "final"
    AMENDED = "amended"
    CANCELLED = "cancelled"


class Observation(BaseModel):
    id: str
    patient_id: str
    encounter_id: Optional[str] = None
    code: str = Field(..., description="LOINC/SNOMED 编码")
    display: str = Field(..., description="显示名称")
    value: Optional[str] = None
    unit: Optional[str] = None
    reference_range: Optional[str] = None
    status: ObservationStatus = ObservationStatus.FINAL
    effective_at: datetime = Field(default_factory=datetime.now)


class LabResult(Observation):
    """检验结果"""
    specimen_type: Optional[str] = None
    method: Optional[str] = None
    abnormal_flag: Optional[str] = None


class VitalSign(Observation):
    """生命体征"""
    body_site: Optional[str] = None
