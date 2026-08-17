import time
import uuid
import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.database.session import SessionLocal
from app.models.entities import AuditLog
from app.security.tokens import decode_access_token

logger = structlog.get_logger()

class AuditRequestMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        started = time.perf_counter()
        response = await call_next(request)
        if request.method in {"POST", "PUT", "PATCH", "DELETE"} and 200 <= response.status_code < 300:
            actor_id = None
            authorization = request.headers.get("authorization", "")
            if authorization.lower().startswith("bearer "):
                try:
                    actor_id = uuid.UUID(decode_access_token(authorization[7:])["sub"])
                except Exception:
                    pass
            try:
                async with SessionLocal() as session:
                    session.add(AuditLog(actor_id=actor_id, action=request.method, resource=request.url.path, resource_id=None, metadata_json={"status": response.status_code, "client_ip": request.client.host if request.client else None}))
                    await session.commit()
            except Exception:
                # Audit availability must not turn a successful user action into a 500.
                logger.exception("audit_log_write_failed", path=request.url.path)
        logger.info("api_request", method=request.method, path=request.url.path, status=response.status_code, duration_ms=round((time.perf_counter() - started) * 1000, 2), client=request.client.host if request.client else None)
        return response
