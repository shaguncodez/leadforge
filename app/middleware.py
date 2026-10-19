import logging
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("leadforge.access")
logging.basicConfig(level=logging.INFO)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that logs request method, path, response status, and processing duration."""

    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()
        client_ip = request.client.host if request.client else "unknown"

        try:
            response = await call_next(request)
            process_time = (time.perf_counter() - start_time) * 1000
            logger.info(
                f"{client_ip} - \"{request.method} {request.url.path}\" "
                f"{response.status_code} ({process_time:.2f}ms)"
            )
            response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
            return response
        except Exception as exc:
            process_time = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"{client_ip} - \"{request.method} {request.url.path}\" "
                f"ERROR: {str(exc)} ({process_time:.2f}ms)"
            )
            raise exc
