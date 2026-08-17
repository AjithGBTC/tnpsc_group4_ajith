"""Fail-open Redis JSON cache used for read-heavy public/admin projections."""
import json
from typing import Any
from redis.asyncio import Redis
from app.core.config import get_settings


class CacheService:
    def __init__(self) -> None:
        self.client = Redis.from_url(get_settings().redis_url, decode_responses=True, socket_connect_timeout=0.2, socket_timeout=0.2)

    async def get(self, key: str) -> Any | None:
        try:
            value = await self.client.get(key)
            return json.loads(value) if value else None
        except Exception:
            return None

    async def set(self, key: str, value: Any, seconds: int = 300) -> None:
        try:
            await self.client.set(key, json.dumps(value, default=str), ex=seconds)
        except Exception:
            pass

    async def delete(self, *keys: str) -> None:
        try:
            if keys:
                await self.client.delete(*keys)
        except Exception:
            pass
