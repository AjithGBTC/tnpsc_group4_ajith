import structlog
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from prometheus_client import make_asgi_app
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.middleware.audit import AuditRequestMiddleware

settings = get_settings()
structlog.configure(processors=[structlog.processors.TimeStamper(fmt="iso"), structlog.processors.JSONRenderer()])
app = FastAPI(title="Exam Platform API", version="1.0.0", openapi_url="/api/v1/openapi.json", docs_url="/docs", redoc_url="/redoc")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"], max_age=600)
app.add_middleware(AuditRequestMiddleware)
app.include_router(api_router, prefix="/api/v1")
Path("uploads").mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/metrics", make_asgi_app())

@app.get("/health/live", tags=["Health"])
async def live() -> dict[str, str]: return {"status": "ok"}

@app.get("/health/ready", tags=["Health"])
async def ready() -> dict[str, str]: return {"status": "ready", "environment": settings.app_env}
