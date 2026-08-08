from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.dependencies.auth import current_user
from app.schemas.auth import LoginRequest, OtpRequest, OtpVerifyRequest, RefreshRequest, TokenPair, UserResponse
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/request-otp")
async def request_otp(payload: OtpRequest, db: AsyncSession = Depends(get_db)) -> dict:
    # A real provider (MSG91/Twilio) should be invoked by the background worker here.
    record = await AuthService(db).request_otp(payload.phone)
    response = {"message": "OTP sent", "phone": payload.phone}
    if getattr(record, "code_for_development", None): response["otp_for_testing"] = record.code_for_development
    return response

@router.post("/verify-otp", response_model=TokenPair)
async def verify_otp(payload: OtpVerifyRequest, db: AsyncSession = Depends(get_db)) -> TokenPair:
    return await AuthService(db).verify_phone_otp(payload.phone, payload.otp, payload.display_name, payload.device_name)

@router.post("/logout", status_code=204)
async def logout(payload: RefreshRequest, db: AsyncSession = Depends(get_db)) -> None:
    await AuthService(db).logout(payload.refresh_token)

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
