from datetime import UTC, datetime, timedelta
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import get_settings
from app.models.entities import RefreshSession, User
from app.repositories.users import UserRepository
from app.schemas.auth import TokenPair
from app.security.tokens import create_access_token, digest, new_refresh_token, verify_password


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
    async def _issue(self, user: User, device_name: str | None) -> TokenPair:
        raw_refresh = new_refresh_token()
        self.db.add(RefreshSession(user_id=user.id, token_hash=digest(raw_refresh), device_name=device_name, expires_at=datetime.now(UTC) + timedelta(days=get_settings().refresh_token_days)))
        await self.db.commit()
        return TokenPair(access_token=create_access_token(str(user.id), await self.users.permissions(user.id)), refresh_token=raw_refresh)
