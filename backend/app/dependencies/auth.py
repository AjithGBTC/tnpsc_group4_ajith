import uuid
from collections.abc import Callable
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.models.entities import User
from app.security.tokens import decode_access_token

bearer = HTTPBearer(auto_error=True)

async def current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer), db: AsyncSession = Depends(get_db)) -> User:
    try: payload = decode_access_token(credentials.credentials); user_id = uuid.UUID(payload["sub"])
    except Exception as exc: raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc
    user = await db.get(User, user_id)
    if not user or user.deleted_at or user.status != "active": raise HTTPException(status_code=401, detail="Account unavailable")
    return user

def require_permissions(*required: str) -> Callable:
    async def check(credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> None:
        try: granted = set(decode_access_token(credentials.credentials).get("per", []))
        except Exception as exc: raise HTTPException(status_code=401, detail="Invalid or expired token") from exc
        if "*" not in granted and not set(required).issubset(granted): raise HTTPException(status_code=403, detail="Insufficient permission")
    return check
