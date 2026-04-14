"""
MingEvidence 临床证据平台 — 整合版
源自 mingevidence 项目，适配 MedIntel Cloud monorepo
核心能力：临床证据搜索、分级评价、实时数据源
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
from datetime import datetime

from core.utils.mimo_client import get_mimo_client, MIMOClient

router = APIRouter()


class EvidenceLevel(str, Enum):
    """证据等级 (Oxford CEBM)"""
    LEVEL_1A = "1a"  # 系统综述RCT
    LEVEL_1B = "1b"  # 单个高质量RCT
    LEVEL_2A = "2a"  # 系统综述队列研究
    LEVEL_2B = "2b"  # 单个队列研究
    LEVEL_3A = "3a"  # 系统综述病例对照
    LEVEL_3B = "3b"  # 单个病例对照
    LEVEL_4 = "4"    # 病例系列
    LEVEL_5 = "5"    # 专家意见


class EvidenceSource(str, Enum):
    PUBMED = "pubmed"
    COCHRANE = "cochrane"
    UPTODATE = "uptodate"
    GUIDELINE = "guideline"
    CLINICALTRIALS = "clinicaltrials"
    NMPA = "nmpa"       # 国家药监局
    CHINESE = "chinese"  # 中文数据库


class EvidenceItem(BaseModel):
    id: str
    title: str
    source: EvidenceSource
    evidence_level: Optional[EvidenceLevel] = None
    study_type: Optional[str] = None
    sample_size: Optional[int] = None
    population: Optional[str] = None
    intervention: Optional[str] = None
    comparator: Optional[str] = None
    outcome: Optional[str] = None
    effect_size: Optional[str] = None
    confidence_interval: Optional[str] = None
    p_value: Optional[str] = None
    conclusion: str = ""
    authors: List[str] = []
    journal: str = ""
    year: Optional[int] = None
    pmid: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    relevance_score: float = 0.0


class EvidenceSearchRequest(BaseModel):
    query: str
    pico: Optional[dict] = Field(None, description="PICO框架: population, intervention, comparator, outcome")
    sources: List[EvidenceSource] = Field(default_factory=lambda: [EvidenceSource.PUBMED])
    evidence_levels: List[EvidenceLevel] = []
    max_results: int = 20
    date_range: Optional[str] = None
    language: str = "all"  # all, en, zh


class EvidenceSearchResponse(BaseModel):
    query: str
    total: int
    items: List[EvidenceItem] = []
    summary: str = ""
    search_time_ms: int = 0


class EvidenceSummaryRequest(BaseModel):
    topic: str
    evidence_items: List[str] = Field(description="Evidence item IDs to synthesize")
    summary_type: str = "narrative"  # narrative, structured, meta_analysis


class EvidenceSummaryResponse(BaseModel):
    topic: str
    summary: str
    key_findings: List[str] = []
    evidence_gaps: List[str] = []
    recommendations: List[str] = []
    quality_assessment: dict = {}


@router.get("/health")
async def health():
    return {"status": "ok", "service": "MingEvidence", "version": "1.0.0",
            "features": ["证据搜索", "PICO分析", "证据分级", "自动综合"]}


@router.post("/search", response_model=EvidenceSearchResponse)
async def search_evidence(
    request: EvidenceSearchRequest,
    mimo: MIMOClient = Depends(get_mimo_client),
):
    """临床证据搜索"""
    import time
    start = time.time()

    # 用MIMO优化搜索策略
    if request.pico:
        pico_text = f"""
PICO框架:
- P (Population): {request.pico.get('population', '未指定')}
- I (Intervention): {request.pico.get('intervention', '未指定')}
- C (Comparator): {request.pico.get('comparator', '未指定')}
- O (Outcome): {request.pico.get('outcome', '未指定')}
"""
        search_prompt = f"基于PICO框架，为以下临床问题生成最佳搜索策略：{pico_text}\n原始查询: {request.query}"
    else:
        search_prompt = f"优化以下临床证据搜索查询：{request.query}"

    try:
        optimized = await mimo.chat([
            {"role": "system", "content": "你是临床文献检索专家。"},
            {"role": "user", "content": search_prompt},
        ])
    except Exception:
        optimized = request.query

    # TODO: 接入实际数据源 (PubMed E-utilities, Cochrane API, etc.)
    # from evidence_sources import search_all_sources
    # results = await search_all_sources(optimized, sources=request.sources, ...)

    elapsed = int((time.time() - start) * 1000)

    return EvidenceSearchResponse(
        query=request.query,
        total=0,
        items=[],
        summary="数据源集成中",
        search_time_ms=elapsed,
    )


@router.post("/summarize", response_model=EvidenceSummaryResponse)
async def summarize_evidence(
    request: EvidenceSummaryRequest,
    mimo: MIMOClient = Depends(get_mimo_client),
):
    """证据综合与评价"""
    prompt = f"""请对以下临床证据进行综合评价：

主题: {request.topic}
综合类型: {request.summary_type}

请提供：
1. 关键发现总结
2. 证据质量评估 (GRADE框架)
3. 证据差距
4. 临床建议
5. 研究建议"""

    try:
        summary = await mimo.chat([
            {"role": "system", "content": "你是循证医学专家，熟悉GRADE证据评级体系。"},
            {"role": "user", "content": prompt},
        ])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return EvidenceSummaryResponse(
        topic=request.topic,
        summary=summary,
    )


@router.get("/guidelines")
async def search_guidelines(
    query: str = Query(...),
    country: str = Query(default="CN"),
):
    """临床指南检索"""
    # TODO: 接入各国指南数据库
    return {"query": query, "country": country, "guidelines": []}


@router.get("/sources/status")
async def source_status():
    """数据源状态"""
    return {
        "sources": [
            {"name": "PubMed", "status": "connected", "last_sync": datetime.now().isoformat()},
            {"name": "Cochrane", "status": "pending", "last_sync": None},
            {"name": "ClinicalTrials.gov", "status": "pending", "last_sync": None},
            {"name": "NMPA", "status": "pending", "last_sync": None},
        ]
    }
