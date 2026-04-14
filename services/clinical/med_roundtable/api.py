"""
🩺 临床科研圆桌 — API 路由
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
    return HealthResponse(status="ok", service="MedRoundTable", version="1.0.0")


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
    """🩺 临床科研圆桌 — 核心查询接口"""
    # TODO: 接入原项目逻辑
    return QueryResponse(
        result=f"[MedRoundTable] 处理查询: {request.query}",
        confidence=0.85,
        sources=[],
    )
