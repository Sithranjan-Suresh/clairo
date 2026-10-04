import logging
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import AUTO_MIGRATE, GROQ_API_KEY, WORKER_ENABLED
from app.database import SessionLocal
from app.limiter import limiter
from app.observability import configure_logging, install_observability
from app.routes import (
    analytics, appeal, audit, auth, claims, export, insforge, jobs,
    policies, prior_auth, rag, risk, system, voice,
)
from app.security.auth import get_current_user

configure_logging()
logger = logging.getLogger(__name__)

if not GROQ_API_KEY:
    logger.critical(
        "GROQ_API_KEY is not set — every extraction, classification, risk, "
        "appeal, and voice endpoint will fail. Set it before serving traffic."
    )

MAX_JSON_BODY_BYTES = 2 * 1024 * 1024  # 2 MB — generous for JSON payloads


@asynccontextmanager
async def lifespan(app: FastAPI):
    worker = None
    try:
        if AUTO_MIGRATE:
            from app.migrations import run_migrations
            run_migrations()
        from app.services.auth_service import bootstrap_admin
        with SessionLocal() as db:
            bootstrap_admin(db)
        try:
            from app.services.policy_service import sync_catalog
            with SessionLocal() as db:
                sync_catalog(db)
        except Exception:
            logger.exception("policy catalog sync failed (continuing without it)")
        if WORKER_ENABLED:
            from app.jobs.worker import Worker
            worker = Worker()
            worker.start()
    except Exception:
        logger.exception("startup failed")
        raise
    yield
    if worker:
        worker.stop()


app = FastAPI(title="CLAIRO API", version="2.0.0", lifespan=lifespan)


def _rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"error": "Rate limit exceeded. Please slow down and try again shortly.",
                 "detail": "Rate limit exceeded. Please slow down and try again shortly."},
        headers={"Retry-After": "30"},
    )


app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


@app.middleware("http")
async def reject_oversized_bodies(request: Request, call_next):
    """Defense-in-depth against huge JSON payloads (multipart uploads enforce
    their own per-route limits)."""
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit():
        if int(content_length) > MAX_JSON_BODY_BYTES and "multipart" not in (
            request.headers.get("content-type") or ""
        ):
            return JSONResponse(status_code=413, content={"detail": "Request body too large."})
    return await call_next(request)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# Localhost dev ports + production origins from CORS_ORIGINS (comma-separated).
_default_origins = [
    "http://localhost:5173", "http://localhost:5174", "http://localhost:3000",
    "http://127.0.0.1:5173", "http://127.0.0.1:5174", "http://127.0.0.1:3000",
]
_extra_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_default_origins + _extra_origins,
    # Preview-hosting subdomains. Safe alongside a broad regex because
    # allow_credentials is False: auth is a Bearer header, never a cookie.
    allow_origin_regex=r"https://.*\.(vercel|netlify|onrender|railway)\.app",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

# Registered last so it wraps everything above and sees every request.
install_observability(app)

authed = [Depends(get_current_user)]

# Public
app.include_router(system.router)
app.include_router(auth.router)
# Authenticated (per-route RBAC inside)
app.include_router(claims.router)
app.include_router(jobs.router)
app.include_router(policies.router)
app.include_router(audit.router)
# Authenticated stateless/legacy tool endpoints (also used by the MCP server)
app.include_router(rag.router, prefix="/rag", dependencies=authed)
app.include_router(appeal.router, prefix="/appeal", dependencies=authed)
app.include_router(risk.router, prefix="/risk", dependencies=authed)
app.include_router(export.router, prefix="/export", dependencies=authed)
app.include_router(analytics.router, prefix="/analytics")
app.include_router(voice.router, prefix="/voice")
app.include_router(prior_auth.router, prefix="/api", dependencies=authed)
app.include_router(insforge.router, prefix="/insforge")


@app.get("/")
def root():
    return {"message": "CLAIRO backend is running", "version": app.version, "docs": "/docs"}
