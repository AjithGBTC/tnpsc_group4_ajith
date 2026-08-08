from datetime import UTC, datetime, timedelta
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import get_settings
from app.models.entities import OTP, RefreshSession, User
from app.repositories.users import UserRepository
from app.schemas.auth import TokenPair
from app.security.tokens import create_access_token, digest, hash_password, new_refresh_token, verify_password


class AuthService:
    def __init__(self, db: AsyncSession): self.db, self.users = db, UserRepository(db)
    async def login(self, email: str, password: str, device_name: str | None) -> TokenPair:
        user = await self.users.by_email(email)
        if not user or not verify_password(password, user.password_hash) or user.status != "active":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        return await self._issue(user, device_name)
    async def refresh(self, refresh_token: str) -> TokenPair:
        session = await self.db.scalar(select(RefreshSession).where(RefreshSession.token_hash == digest(refresh_token), RefreshSession.revoked_at.is_(None), RefreshSession.expires_at > datetime.now(UTC)))
        if not session: raise HTTPException(status_code=401, detail="Refresh session expired or revoked")
        session.revoked_at = datetime.now(UTC)  # rotation prevents replay
        user = await self.db.get(User, session.user_id)
        return await self._issue(user, session.device_name)
    async def request_otp(self, phone: str) -> None:
        settings = get_settings()
        # Use a random 4 digit code. Delivery is intentionally isolated here for SMS-provider integration.
        import secrets
        code = f"{secrets.randbelow(10000):04d}"
        record = OTP(phone=phone, code_hash=digest(code), expires_at=datetime.now(UTC) + timedelta(minutes=settings.otp_ttl_minutes))
        self.db.add(record)
        await self.db.commit()
        # Never log the code. Configure an SMS provider in deployment to deliver it.
        if settings.app_env != "production":
            record.code_for_development = code  # type: ignore[attr-defined]
        return record  # type: ignore[return-value]
    async def verify_phone_otp(self, phone: str, otp: str, display_name: str | None, device_name: str | None = "mobile") -> TokenPair:
        settings = get_settings()
        record = await self.db.scalar(select(OTP).where(OTP.phone == phone, OTP.consumed_at.is_(None), OTP.expires_at > datetime.now(UTC)).order_by(OTP.created_at.desc()))
        if not record or record.attempts >= settings.otp_max_attempts or digest(otp) != record.code_hash:
            if record:
                record.attempts += 1
                await self.db.commit()
            raise HTTPException(status_code=401, detail="Invalid OTP")
        record.consumed_at = datetime.now(UTC)
        user = await self.db.scalar(select(User).where(User.phone == phone, User.deleted_at.is_(None)))
        if not user:
            user = User(phone=phone, email=f"{phone}@mobile.local", display_name=display_name or "TNPSC Student", password_hash=hash_password(new_refresh_token()), is_verified=True)
            self.db.add(user)
            await self.db.flush()
        elif user.status != "active":
            raise HTTPException(status_code=401, detail="Account unavailable")
        return await self._issue(user, device_name)
    async def logout(self, refresh_token: str) -> None:
        session = await self.db.scalar(select(RefreshSession).where(RefreshSession.token_hash == digest(refresh_token), RefreshSession.revoked_at.is_(None)))
        if session:
            session.revoked_at = datetime.now(UTC)
            await self.db.commit()
    async def _issue(self, user: User, device_name: str | None) -> TokenPair:
        raw_refresh = new_refresh_token()
        self.db.add(RefreshSession(user_id=user.id, token_hash=digest(raw_refresh), device_name=device_name, expires_at=datetime.now(UTC) + timedelta(days=get_settings().refresh_token_days)))
        await self.db.commit()
        return TokenPair(access_token=create_access_token(str(user.id), await self.users.permissions(user.id)), refresh_token=raw_refresh)
