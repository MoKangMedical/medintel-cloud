"""
源自 digital-sage 项目，适配 MedIntel Cloud monorepo
"""

from fastapi import FastAPI
from .api import router

app = FastAPI(title="Digital Sage", version="1.0.0")
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
