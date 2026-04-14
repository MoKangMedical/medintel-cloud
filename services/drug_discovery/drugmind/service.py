"""
🤖 DrugMind — 药物研发数字分身协作平台服务入口
"""

import logging
from fastapi import FastAPI
from .api import router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="DrugMind - Digital Twin Collaboration",
    version="1.0.0",
    description="数字分身协作 · 决策追踪 · Second Me集成",
)

app.include_router(router, prefix="/twins", tags=["DrugMind"])


@app.on_event("startup")
async def startup():
    logger.info("🤖 DrugMind service started")


@app.on_event("shutdown")
async def shutdown():
    logger.info("🤖 DrugMind service stopped")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
