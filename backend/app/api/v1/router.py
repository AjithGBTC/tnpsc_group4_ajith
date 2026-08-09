from fastapi import APIRouter
from app.api.v1.routes import admin, auth, content, mobile, platform

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(content.router)
api_router.include_router(mobile.router)
api_router.include_router(platform.router)
api_router.include_router(admin.router)
