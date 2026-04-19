import logging
import time
from fastapi import FastAPI
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from backend.api.listener import router as listener_router
from backend.api.dashboard import router as dashboard_router
from backend.api.debug import router as debug_router
from backend.api.air_quality import router as air_quality_router

# Initialize Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("signal_pipeline")

app = FastAPI(
    title="Gabès Copilot API",
    description="Single entrypoint for inbound local reports.",
    version="1.0"
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    started = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - started) * 1000
    logger.info(
        "HTTP %s %s -> %s (%.1f ms)",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development; refine for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incorporate the inbound REST listener router
app.include_router(listener_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(debug_router, prefix="/api/v1")
app.include_router(air_quality_router, prefix="/api/v1")


@app.on_event("startup")
async def startup_log_routes():
    logger.info("Backend startup complete. Report endpoint: POST /api/v1/report")

@app.get("/")
def read_root():
    return {"status": "Gabès Copilot API is active and listening"}
