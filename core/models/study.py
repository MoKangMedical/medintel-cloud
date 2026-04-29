"""
Study/ClinicalTrial/Evidence 数据模型
"""

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field


class Study(BaseModel):
    """研究项目"""
    id: str
    title: str
    study_type: str  # observational, interventional, meta_analysis
    phase: Optional[str] = None  # I, II, III, IV
    status: str = "planning"
    principal_investigator: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    sample_size: Optional[int] = None
    nct_id: Optional[str] = None  # ClinicalTrials.gov ID


class ClinicalTrial(Study):
    """临床试验"""
    intervention: Optional[str] = None
    primary_outcome: Optional[str] = None
    secondary_outcomes: list[str] = []
    inclusion_criteria: list[str] = []
    exclusion_criteria: list[str] = []
    sites: list[str] = []
    enrollment: int = 0


class Evidence(BaseModel):
    """临床证据"""
    id: str
    title: str
    source: str  # pubmed, cochrane, guideline, etc.
    evidence_level: Optional[str] = None  # 1a, 1b, 2a, 2b, 3, 4, 5
    study_design: Optional[str] = None
    conclusion: Optional[str] = None
    pmid: Optional[str] = None
    doi: Optional[str] = None
    published_at: Optional[date] = None
    url: Optional[str] = None
    fetched_at: datetime = Field(default_factory=datetime.now)
