"""
Molecule/Compound/Target 数据模型 — 药物发现专用
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class Target(BaseModel):
    """药物靶点"""
    id: str
    name: str
    gene_symbol: Optional[str] = None
    uniprot_id: Optional[str] = None
    organism: str = "Homo sapiens"
    target_type: Optional[str] = None  # enzyme, receptor, ion_channel, etc.
    disease_associations: list[str] = []
    druggability_score: Optional[float] = None


class Molecule(BaseModel):
    """分子结构"""
    id: str
    smiles: str = Field(..., description="SMILES表示")
    inchi_key: Optional[str] = None
    molecular_weight: Optional[float] = None
    logp: Optional[float] = None
    hbd: Optional[int] = None  # H-bond donors
    hba: Optional[int] = None  # H-bond acceptors
    tpsa: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.now)


class Compound(Molecule):
    """化合物 — 带活性数据"""
    target_id: Optional[str] = None
    ic50: Optional[float] = None
    ec50: Optional[float] = None
    ki: Optional[float] = None
    selectivity: Optional[dict[str, float]] = None
    admet: Optional[dict] = None
    stage: str = "discovery"  # discovery, lead, preclinical, clinical
