"""
Medication 数据模型
"""

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field


class Medication(BaseModel):
    id: str
    name: str = Field(..., description="药品通用名")
    brand_name: Optional[str] = None
    atc_code: Optional[str] = Field(None, description="ATC编码")
    dosage_form: Optional[str] = None
    strength: Optional[str] = None
    manufacturer: Optional[str] = None


class Prescription(BaseModel):
    id: str
    patient_id: str
    encounter_id: Optional[str] = None
    medication_id: str
    dosage: str
    frequency: str
    route: str = "oral"
    start_date: date
    end_date: Optional[date] = None
    prescriber_id: Optional[str] = None
    status: str = "active"
    notes: Optional[str] = None
