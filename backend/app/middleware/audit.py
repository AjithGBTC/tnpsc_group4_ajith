import time
import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger()

class AuditRequestMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        started = time.perf_counter()
        response = await call_next(request)
        logger.info("api_request", method=request.method, path=request.url.path, status=response.status_code, duration_ms=round((time.perf_counter() - started) * 1000, 2), client=request.client.host if request.client else None)
        return response
