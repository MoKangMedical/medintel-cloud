"""
Ponder 知识工作流 — 整合版
源自 ponder-knowledge-platform 项目
核心能力：资料导入→引用→洞察→报告
"""

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from enum import Enum
import uuid
from datetime import datetime

from core.utils.mimo_client import get_mimo_client, MIMOClient

router = APIRouter()


class SourceType(str, Enum):
    PDF = "pdf"
    URL = "url"
    TEXT = "text"
    DOI = "doi"
    PMID = "pmid"


class KnowledgeSource(BaseModel):
    id: str
    type: SourceType
    title: str
    content: str = ""
    metadata: Dict[str, str] = {}
    tags: List[str] = []
    created_at: str = ""


class InsightRequest(BaseModel):
    source_ids: List[str]
    question: str
    depth: str = "deep"  # shallow, medium, deep


class Insight(BaseModel):
    id: str
    content: str
    confidence: float = 0.0
    supporting_sources: List[str] = []
    reasoning: str = ""


class ReportRequest(BaseModel):
    title: str
    source_ids: List[str]
    report_type: str = "research_brief"  # research_brief, literature_review, executive_summary
    audience: str = "expert"  # expert, general, executive
    model: Optional[str] = "mimo-v2-pro"


class Report(BaseModel):
    id: str
    title: str
    content: str
    sections: Dict[str, str] = {}
    citations: List[Dict[str, str]] = []
    generated_at: str = ""


@router.get("/health")
async def health():
    return {"status": "ok", "service": "Ponder", "version": "1.0.0",
            "workflow": "导入→引用→洞察→报告"}


@router.post("/sources/import")
async def import_source(
    source_type: SourceType,
    content: Optional[str] = None,
    file: Optional[UploadFile] = File(None),
):
    """导入知识源"""
    source_id = str(uuid.uuid4())
    return KnowledgeSource(
        id=source_id,
        type=source_type,
        title=file.filename if file else f"Source {source_id[:8]}",
        content=content or "",
        created_at=datetime.now().isoformat(),
    )


@router.get("/sources")
async def list_sources(
    tag: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
):
    """列出知识源"""
    return {"sources": [], "total": 0, "page": page}


@router.post("/insights", response_model=List[Insight])
async def generate_insights(
    request: InsightRequest,
    mimo: MIMOClient = Depends(get_mimo_client),
):
    """从知识源生成洞察"""
    prompt = f"""基于以下知识源，回答问题并提供深度洞察：

问题: {request.question}
深度: {request.depth}
知识源IDs: {', '.join(request.source_ids)}

请提供：
1. 核心答案
2. 支撑证据
3. 推理过程
4. 相关引用"""

    try:
        analysis = await mimo.chat([
            {"role": "system", "content": "你是知识分析师，从多个来源提取洞察并综合分析。"},
            {"role": "user", "content": prompt},
        ])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return [Insight(
        id=str(uuid.uuid4()),
        content=analysis,
        confidence=0.85,
        reasoning="基于AI综合分析",
    )]


@router.post("/reports", response_model=Report)
async def generate_report(
    request: ReportRequest,
    mimo: MIMOClient = Depends(get_mimo_client),
):
    """生成知识报告"""
    prompt = f"""请生成一份专业的{request.report_type}报告：

标题: {request.title}
目标读者: {request.audience}
知识源: {', '.join(request.source_ids)}

报告类型说明：
- research_brief: 研究简报，2-3页
- literature_review: 文献综述，系统性
- executive_summary: 执行摘要，1页

请生成结构化报告。"""

    try:
        content = await mimo.chat([
            {"role": "system", "content": f"你是专业报告撰写者，目标读者是{request.audience}。"},
            {"role": "user", "content": prompt},
        ], model=request.model)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return Report(
        id=str(uuid.uuid4()),
        title=request.title,
        content=content,
        generated_at=datetime.now().isoformat(),
    )


@router.post("/citations/extract")
async def extract_citations(
    text: str,
    mimo: MIMOClient = Depends(get_mimo_client),
):
    """从文本中提取引用"""
    prompt = f"从以下文本中提取所有引用/参考文献，以结构化格式输出：\n{text[:3000]}"
    try:
        citations = await mimo.chat([
            {"role": "system", "content": "你是引用提取专家。"},
            {"role": "user", "content": prompt},
        ])
        return {"citations": citations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
