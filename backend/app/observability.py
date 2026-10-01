import logging
import time
import uuid

from starlette.requests import Request

from app.metrics import REQUEST_DURATION_SECONDS, REQUESTS_TOTAL

log = logging.getLogger("app.access")


async def observability_middleware(request: Request, call_next):
    """Tag every request with an id, time it, and emit one structured log line plus metrics.

    Wraps everything else (CORS, rate limiting) so a 429 or a CORS rejection is counted and
    logged too, not just requests that reach a route handler.
    """
    request_id = uuid.uuid4().hex
    start = time.perf_counter()
    response = None
    try:
        response = await call_next(request)
        return response
    finally:
        duration = time.perf_counter() - start
        route = request.scope.get("route")
        path_template = route.path if route else request.url.path
        status_code = response.status_code if response is not None else 500
        REQUESTS_TOTAL.labels(request.method, path_template, str(status_code)).inc()
        REQUEST_DURATION_SECONDS.labels(request.method, path_template).observe(duration)
        if response is not None:
            response.headers["X-Request-ID"] = request_id
        log.info(
            "request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": path_template,
                "status_code": status_code,
                "duration_ms": round(duration * 1000, 2),
            },
        )
