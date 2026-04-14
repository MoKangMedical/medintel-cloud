"""
统一数据模型 — FHIR/RWD/EHR 标准
所有服务共享的数据契约
"""

from .patient import Patient, PatientSummary
from .encounter import Encounter, EncounterType
from .observation import Observation, LabResult, VitalSign
from .medication import Medication, Prescription
from .condition import Condition, Diagnosis
from .molecule import Molecule, Compound, Target
from .study import Study, ClinicalTrial, Evidence

__all__ = [
    "Patient", "PatientSummary",
    "Encounter", "EncounterType",
    "Observation", "LabResult", "VitalSign",
    "Medication", "Prescription",
    "Condition", "Diagnosis",
    "Molecule", "Compound", "Target",
    "Study", "ClinicalTrial", "Evidence",
]
