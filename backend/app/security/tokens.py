import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from jose import jwt
from pwdlib import PasswordHash
from app.core.config import get_settings

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str: return password_hash.hash(password)
def verify_password(password: str, hashed: str) -> bool: return password_hash.verify(password, hashed)
def digest(token: str) -> str: return hashlib.sha256(token.encode()).hexdigest()


def create_access_token(subject: str, permissions: list[str]) -> str:
    settings = get_settings()
    payload = {"sub": subject, "per": permissions, "typ": "access", "exp": datetime.now(UTC) + timedelta(minutes=settings.access_token_minutes)}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def new_refresh_token() -> str: return secrets.token_urlsafe(48)


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    if payload.get("typ") != "access": raise ValueError("Invalid token type")
    return payload
