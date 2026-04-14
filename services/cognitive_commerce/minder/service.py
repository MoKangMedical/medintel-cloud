"""
🍐 念念 (Minder) — 服务入口

智能语音提醒服务，珍藏每一个念想。
"""

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from .api import router

app = FastAPI(title="Minder - 念念", version="0.1.0")
app.include_router(router, prefix="/api/minder")

# 静态文件目录（如果存在的话）
_STATIC_DIR = Path(__file__).parent / "static"
if _STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

    @app.get("/")
    async def index():
        index_file = _STATIC_DIR / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return {"message": "🍐 念念 — 你的第二记忆"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8200)
