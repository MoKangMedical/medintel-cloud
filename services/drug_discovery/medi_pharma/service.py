"""
🔬 MediPharma — AI药物发现平台服务入口
"""

import logging
from fastapi import FastAPI
from .api import router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="MediPharma - AI Drug Discovery",
    version="1.0.0",
    description="靶点发现 · 分子生成 · 虚拟筛选 · ADMET预测",
)

app.include_router(router, prefix="/pharma", tags=["MediPharma"])


@app.on_event("startup")
async def startup():
    logger.info("🔬 MediPharma service started")


@app.on_event("shutdown")
async def shutdown():
    logger.info("🔬 MediPharma service stopped")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
