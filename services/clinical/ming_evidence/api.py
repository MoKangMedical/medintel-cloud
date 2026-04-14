"""
📚 临床证据平台 — API 路由
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok", service="MingEvidence", version="1.0.0")


class QueryRequest(BaseModel):
    query: str
    context: Optional[dict] = None
    model: Optional[str] = "mimo-v2-pro"


class QueryResponse(BaseModel):
    result: str
    confidence: Optional[float] = None
    sources: list[str] = []


@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """📚 临床证据平台 — 核心查询接口"""
    # TODO: 接入原项目逻辑
    return QueryResponse(
        result=f"[MingEvidence] 处理查询: {request.query}",
        confidence=0.85,
        sources=[],
    )
