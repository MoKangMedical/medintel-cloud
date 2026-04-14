"""
🔬 AI药物发现平台 — 服务入口
"""

import uvicorn
from .api import router
from fastapi import FastAPI

app = FastAPI(title="MediPharma", version="1.0.0")
app.include_router(router, prefix="/pharma")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
