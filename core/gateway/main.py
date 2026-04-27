"""
API Gateway — 统一入口
所有外部请求通过这里路由到各服务模块
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
import structlog

logger = structlog.get_logger()

app = FastAPI(
    title="MedIntel Cloud API",
    description="🏥 全栈医疗AI统一平台 API Gateway",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    logger.info(
        "request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=round(duration * 1000, 2),
    )
    return response


# 健康检查
@app.get("/health")
async def health():
    return {"status": "ok", "service": "medintel-cloud", "version": "1.0.0"}


# 引擎状态
@app.get("/api/v1/engines")
async def list_engines():
    """列出所有可用引擎"""
    return {
        "engines": [
            {"id": "drug_discovery", "name": "药物发现引擎", "status": "active"},
            {"id": "clinical", "name": "临床决策引擎", "status": "active"},
            {"id": "cognitive_commerce", "name": "认知商业引擎", "status": "active"},
            {"id": "knowledge", "name": "知识研究引擎", "status": "active"},
        ]
    }


# --- 药物发现引擎路由 ---
from services.drug_discovery.medi_pharma.api import router as medi_pharma_router
from services.drug_discovery.drugmind.api import router as drugmind_router
from services.drug_discovery.virtual_cell.api import router as virtual_cell_router
from services.drug_discovery.pharma_sim.api import router as pharma_sim_router

app.include_router(medi_pharma_router, prefix="/api/v1/drug-discovery/pharma", tags=["🔬 MediPharma"])
app.include_router(drugmind_router, prefix="/api/v1/drug-discovery/twins", tags=["🤖 DrugMind"])
app.include_router(virtual_cell_router, prefix="/api/v1/drug-discovery/cells", tags=["🧬 VirtualCell"])
app.include_router(pharma_sim_router, prefix="/api/v1/drug-discovery/sim", tags=["📊 PharmaSim"])


# --- 临床决策引擎路由 ---
from services.clinical.medi_chat_rd.api import router as medi_chat_rd_router
from services.clinical.med_roundtable.api import router as med_roundtable_router
from services.clinical.ming_evidence.api import router as ming_evidence_router
from services.clinical.chroni_care.api import router as chroni_care_router

app.include_router(medi_chat_rd_router, prefix="/api/v1/clinical/chat", tags=["🏥 MediChat-RD"])
app.include_router(med_roundtable_router, prefix="/api/v1/clinical/roundtable", tags=["🩺 MedRoundTable"])
app.include_router(ming_evidence_router, prefix="/api/v1/clinical/evidence", tags=["📚 MingEvidence"])
app.include_router(chroni_care_router, prefix="/api/v1/clinical/chronic", tags=["💊 ChroniCare"])


# --- 认知商业引擎路由 ---
from services.cognitive_commerce.medi_slim.api import router as medi_slim_router
from services.cognitive_commerce.tianyan.api import router as tianyan_router
from services.cognitive_commerce.cloud_memorial.api import router as cloud_memorial_router

app.include_router(medi_slim_router, prefix="/api/v1/commerce/slim", tags=["💄 MediSlim"])
app.include_router(tianyan_router, prefix="/api/v1/commerce/tianyan", tags=["👁️ Tianyan"])
app.include_router(cloud_memorial_router, prefix="/api/v1/commerce/memorial", tags=["🌸 CloudMemorial"])


# --- 知识研究引擎路由 ---
from services.knowledge.digital_sage.api import router as digital_sage_router
from services.knowledge.ponder.api import router as ponder_router
from services.knowledge.heor_modeling.api import router as heor_router
from services.knowledge.biostats.api import router as biostats_router

app.include_router(digital_sage_router, prefix="/api/v1/knowledge/sage", tags=["🧠 DigitalSage"])
app.include_router(ponder_router, prefix="/api/v1/knowledge/ponder", tags=["📝 Ponder"])
app.include_router(heor_router, prefix="/api/v1/knowledge/heor", tags=["📈 HEOR"])
app.include_router(biostats_router, prefix="/api/v1/knowledge/biostats", tags=["📊 Biostats"])


# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("unhandled_exception", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)},
    )
