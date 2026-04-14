"""
🔬 MediPharma API — 靶点发现 + 分子生成 + 虚拟筛选 + ADMET预测
整合自 medi-pharma 项目
"""

import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional

logger = logging.getLogger(__name__)
router = APIRouter()


# ─── Request/Response Models ───

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class TargetDiscoveryRequest(BaseModel):
    disease: str = Field(..., description="目标疾病名称")
    max_papers: int = Field(50, ge=1, le=200, description="最大文献数")
    top_n: int = Field(10, ge=1, le=50, description="返回Top N靶点")
    disease_burden: float = Field(0.8, ge=0, le=1, description="疾病负担评分")
    unmet_need: float = Field(0.8, ge=0, le=1, description="未满足需求评分")


class TargetDiscoveryResponse(BaseModel):
    disease: str
    total_candidates: int
    top_targets: list[dict]
    methodology: str
    summary: str


class MolGenRequest(BaseModel):
    target_name: str = Field("", description="靶点名称")
    scaffold: Optional[str] = Field(None, description="起始骨架SMILES")
    n_generate: int = Field(200, ge=10, le=1000, description="生成数量")
    n_optimize: int = Field(50, ge=0, le=200, description="优化迭代数")
    target_mw: Optional[float] = Field(400, description="目标分子量")
    target_logp: Optional[float] = Field(2.5, description="目标LogP")
    top_n: int = Field(20, ge=1, le=100)


class MolGenResponse(BaseModel):
    target: str
    total_generated: int
    valid_molecules: int
    top_candidates: list[dict]
    method: str
    summary: str


class ScreeningRequest(BaseModel):
    target_chembl_id: str = Field(..., description="ChEMBL靶点ID")
    protein_pdb: Optional[str] = Field(None, description="蛋白质PDB文件路径")
    max_compounds: int = Field(500, ge=10, le=5000)
    top_n: int = Field(20, ge=1, le=100)
    use_docking: bool = Field(False, description="是否执行分子对接")


class ScreeningResponse(BaseModel):
    target: str
    total_screened: int
    hits_found: int
    top_candidates: list[dict]
    method: str
    summary: str


class ADMETRequest(BaseModel):
    smiles: str = Field(..., description="分子SMILES字符串")
    batch_smiles: Optional[list[str]] = Field(None, description="批量SMILES（可选）")


class ADMETResponse(BaseModel):
    results: list[dict]
    count: int


# ─── Endpoints ───

@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok", service="MediPharma", version="1.0.0")


@router.post("/target_discovery", response_model=TargetDiscoveryResponse)
async def discover_targets(request: TargetDiscoveryRequest):
    """靶点发现：疾病 → PubMed文献挖掘 + 知识图谱 + 多维评分"""
    from .target_discovery.engine import TargetDiscoveryEngine
    try:
        engine = TargetDiscoveryEngine()
        report = engine.discover_targets(
            disease=request.disease,
            max_papers=request.max_papers,
            top_n=request.top_n,
            disease_burden=request.disease_burden,
            unmet_need=request.unmet_need,
        )
        return TargetDiscoveryResponse(
            disease=report.disease,
            total_candidates=report.total_candidates,
            top_targets=report.top_targets,
            methodology=report.methodology,
            summary=report.summary,
        )
    except Exception as e:
        logger.error(f"Target discovery failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate", response_model=MolGenResponse)
async def generate_molecules(request: MolGenRequest):
    """分子生成：靶点信息 → 片段组装 + 遗传算法优化 → 候选分子"""
    from .molecular_generation.engine import MolecularGenerationEngine
    try:
        engine = MolecularGenerationEngine()
        props = {}
        if request.target_mw: props["mw"] = request.target_mw
        if request.target_logp: props["logp"] = request.target_logp

        report = engine.generate_candidates(
            target_name=request.target_name,
            scaffold=request.scaffold,
            n_generate=request.n_generate,
            n_optimize=request.n_optimize,
            target_properties=props or None,
            top_n=request.top_n,
        )
        return MolGenResponse(
            target=report.target, total_generated=report.total_generated,
            valid_molecules=report.valid_molecules, top_candidates=report.top_candidates,
            method=report.method, summary=report.summary,
        )
    except Exception as e:
        logger.error(f"Molecular generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/screen", response_model=ScreeningResponse)
async def virtual_screen(request: ScreeningRequest):
    """虚拟筛选：靶点 + 化合物库 → Top候选化合物"""
    from .virtual_screening.engine import VirtualScreeningEngine
    try:
        engine = VirtualScreeningEngine()
        result = engine.screen(
            target_chembl_id=request.target_chembl_id,
            protein_pdb=request.protein_pdb,
            max_compounds=request.max_compounds,
            top_n=request.top_n,
            use_docking=request.use_docking,
        )
        return ScreeningResponse(
            target=result.target, total_screened=result.total_screened,
            hits_found=result.hits_found, top_candidates=result.top_candidates,
            method=result.method, summary=result.summary,
        )
    except Exception as e:
        logger.error(f"Virtual screening failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admet", response_model=ADMETResponse)
async def admet_predict(request: ADMETRequest):
    """ADMET预测：SMILES → 吸收/分布/代谢/排泄/毒性 + 合成可及性"""
    from .admet_prediction.engine import ADMETEngine
    try:
        engine = ADMETEngine()
        if request.batch_smiles:
            results = engine.batch_predict(request.batch_smiles)
        else:
            report = engine.predict(request.smiles)
            from dataclasses import asdict
            results = [asdict(report)]
        return ADMETResponse(results=results, count=len(results))
    except Exception as e:
        logger.error(f"ADMET prediction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
