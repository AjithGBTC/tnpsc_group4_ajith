from fastapi import APIRouter
from app.api.v1.routes import auth, content, mobile

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(content.router)
api_router.include_router(mobile.router)
