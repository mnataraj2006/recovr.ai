import time
import uuid
import logging
from collections import defaultdict
from typing import Dict, List
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.config.settings import settings

logger = logging.getLogger(__name__)

class SecurityMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        # IP -> List of timestamps
        self.request_records: Dict[str, List[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next) -> Response:
        # 1. Request ID Handling
        req_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:12]}"
        request.state.request_id = req_id

        # 2. Rate Limiting for sensitive paths
        client_ip = request.client.host if request.client else "127.0.0.1"
        path = request.url.path
        
        sensitive_paths = ["/api/v1/auth/login", "/api/v1/webhooks/payment", "/api/v1/api-keys", "/api/v1/simulation/run"]
        if any(path.startswith(p) for p in sensitive_paths):
            now = time.time()
            cutoff = now - 60.0  # 1 minute window
            
            # Clean old records
            timestamps = [t for t in self.request_records[client_ip] if t > cutoff]
            timestamps.append(now)
            self.request_records[client_ip] = timestamps
            
            if len(timestamps) > settings.RATE_LIMIT_PER_MINUTE:
                logger.warning(f"Rate limit exceeded for IP {client_ip} on path {path} (req_id: {req_id})")
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": {
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": "Too many requests. Please try again later.",
                            "request_id": req_id
                        }
                    },
                    headers={"X-Request-ID": req_id}
                )

        # 3. Process Request
        start_time = time.time()
        try:
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000
            response.headers["X-Request-ID"] = req_id
            logger.info(f"HTTP {request.method} {path} -> {response.status_code} ({duration_ms:.1f}ms) [req_id: {req_id}]")
            return response
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"HTTP {request.method} {path} Exception: {e} ({duration_ms:.1f}ms) [req_id: {req_id}]", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": "An internal server error occurred.",
                        "request_id": req_id
                    }
                },
                headers={"X-Request-ID": req_id}
            )
