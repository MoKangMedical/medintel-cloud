"""
🧬 虚拟细胞Benchmark — 服务入口
"""

import uvicorn
from .api import router
from fastapi import FastAPI

app = FastAPI(title="VirtualCell", version="1.0.0")
app.include_router(router, prefix="/cells")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
