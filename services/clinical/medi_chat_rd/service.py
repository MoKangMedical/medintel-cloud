"""
源自 medichat-rd 项目，适配 MedIntel Cloud monorepo
"""

from fastapi import FastAPI
from .api import router

app = FastAPI(title="Medi Chat Rd", version="2.0.0")
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
