"""Small Redis-backed, fail-open rate limiter for public API endpoints."""
from __future__ import annotations

import time

from fastapi import Request
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self._redis: Redis | None = None

    async def dispatch(self, request: Request, call_next):
        if request.url.path in {"/health/live", "/health/ready", "/metrics"}:
            return await call_next(request)
        settings = get_settings()
        client_ip = request.client.host if request.client else "unknown"
        is_otp = request.url.path.endswith("/auth/request-otp")
        window, limit = (3600, settings.otp_rate_limit_per_hour) if is_otp else (60, settings.request_rate_limit_per_minute)
        key = f"tnpsc:rate:{'otp' if is_otp else 'api'}:{client_ip}:{int(time.time() // window)}"
        try:
            if self._redis is None:
                self._redis = Redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=0.2, socket_timeout=0.2)
            count = await self._redis.incr(key)
            if count == 1:
                await self._redis.expire(key, window)
            if count > limit:
                return JSONResponse({"detail": "Rate limit exceeded"}, status_code=429, headers={"Retry-After": str(window)})
        except Exception:
            # Redis outages must not take the learning API offline; alert on this
            # via infrastructure monitoring and retain endpoint-level validation.
            pass
        return await call_next(request)

    async def close(self) -> None:
        if self._redis:
            await self._redis.aclose()
