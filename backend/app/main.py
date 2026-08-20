import structlog
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from prometheus_client import make_asgi_app
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.middleware.audit import AuditRequestMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.database.session import engine
from sqlalchemy import text

settings = get_settings()
structlog.configure(processors=[structlog.processors.TimeStamper(fmt="iso"), structlog.processors.JSONRenderer()])

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()

app = FastAPI(title="TNPSC Group 4 Learning API", version="1.0.0", openapi_url="/api/v1/openapi.json", docs_url="/docs", redoc_url="/redoc", lifespan=lifespan)
# CORSMiddleware answers browser preflight OPTIONS requests before route
# dependencies run, so the Authorization token is never needed for preflight.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    # Dio's Flutter web adapter sends this header, which makes the browser
    # issue a CORS preflight request before the login request.
    allow_headers=["Accept", "Authorization", "Content-Type", "X-Requested-With"],
    max_age=600,
)
app.add_middleware(AuditRequestMiddleware)
app.add_middleware(RateLimitMiddleware)
app.include_router(api_router, prefix="/api/v1")
Path("uploads").mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/metrics", make_asgi_app())

@app.get("/health/live", tags=["Health"])
async def live() -> dict[str, str]: return {"status": "ok"}

@app.get("/health/ready", tags=["Health"])
async def ready() -> dict[str, str]: return {"status": "ready", "environment": settings.app_env}
