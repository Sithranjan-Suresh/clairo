"""Structured logging, request IDs, and Prometheus metrics."""
import contextvars
import json
import logging
import time
import uuid
from typing import Optional

from fastapi import FastAPI, Request
from prometheus_client import Counter, Histogram

from app.config import LOG_JSON, LOG_LEVEL

request_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "request_id", default=None
)

# --- metrics ------------------------------------------------------------------
HTTP_REQUESTS = Counter(
    "clairo_http_requests_total", "HTTP requests", ["method", "route", "status"]
)
HTTP_LATENCY = Histogram(
    "clairo_http_request_duration_seconds", "HTTP request latency", ["method", "route"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60),
)
LLM_CALLS = Counter("clairo_llm_calls_total", "LLM calls", ["task", "outcome"])
LLM_LATENCY = Histogram(
    "clairo_llm_call_duration_seconds", "LLM call latency", ["task"],
    buckets=(0.25, 0.5, 1, 2, 5, 10, 20, 40, 60),
)
JOBS = Counter("clairo_jobs_total", "Background jobs finished", ["type", "outcome"])
JOB_LATENCY = Histogram(
    "clairo_job_duration_seconds", "Background job runtime", ["type"],
    buckets=(0.5, 1, 2, 5, 10, 20, 40, 60, 120),
)
CACHE_EVENTS = Counter("clairo_cache_events_total", "Cache lookups", ["namespace", "result"])


# --- logging ------------------------------------------------------------------
class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        rid = request_id_var.get()
        if rid:
            entry["request_id"] = rid
        extra = getattr(record, "ctx", None)
        if extra:
            entry.update(extra)
        if record.exc_info:
            entry["exc"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)


def configure_logging() -> None:
    handler = logging.StreamHandler()
    if LOG_JSON:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(LOG_LEVEL)


def client_ip(request: Request) -> str:
    """Real client IP. Behind Render/Cloudflare the socket peer is the proxy,
    so trust the first X-Forwarded-For hop (the platform sets it)."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def install_observability(app: FastAPI) -> None:
    log = logging.getLogger("clairo.access")

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
        token = request_id_var.set(rid)
        start = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = rid
            return response
        finally:
            elapsed = time.perf_counter() - start
            route = request.scope.get("route")
            route_path = getattr(route, "path", None) or "unmatched"
            HTTP_REQUESTS.labels(request.method, route_path, str(status_code)).inc()
            HTTP_LATENCY.labels(request.method, route_path).observe(elapsed)
            if route_path not in ("/health", "/metrics"):
                log.info(
                    "%s %s -> %s", request.method, request.url.path, status_code,
                    extra={"ctx": {
                        "method": request.method, "path": request.url.path,
                        "status": status_code, "duration_ms": round(elapsed * 1000, 1),
                        "ip": client_ip(request),
                    }},
                )
            request_id_var.reset(token)
