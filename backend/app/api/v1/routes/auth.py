from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.dependencies.auth import current_user
from app.schemas.auth import LoginRequest, RefreshRequest, TokenPair, UserResponse
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=TokenPair)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenPair:
    return await AuthService(db).login(str(payload.email), payload.password, payload.device_name)

@router.post("/refresh", response_model=TokenPair)
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenPair:
    return await AuthService(db).refresh(payload.refresh_token)

@router.get("/me", response_model=UserResponse)
async def me(user=Depends(current_user), db: AsyncSession = Depends(get_db)) -> UserResponse:
    from app.repositories.users import UserRepository
    repo = UserRepository(db)
    return UserResponse(id=str(user.id), email=user.email, display_name=user.display_name, roles=await repo.role_names(user.id))
