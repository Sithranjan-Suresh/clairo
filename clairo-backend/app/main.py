import logging
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.database import engine, Base
from app.limiter import limiter
from app.models import DenialClaim

from app.routes.upload import router as upload_router
from app.routes.rag import router as rag_router
from app.routes.appeal import router as appeal_router
from app.routes.risk import router as risk_router
from app.routes.export import router as export_router
from app.routes.analytics import router as analytics_router
from app.routes.voice import router as voice_router
from app.routes.prior_auth import prior_auth_check_documents, router as prior_auth_router
from app.routes.insforge import router as insforge_router

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

if not os.getenv("GROQ_API_KEY"):
    logger.critical(
        "GROQ_API_KEY is not set — every extraction, classification, risk, "
        "appeal, and voice endpoint will fail. Set it before serving traffic."
    )

MAX_JSON_BODY_BYTES = 2 * 1024 * 1024  # 2 MB — generous for JSON claim/appeal payloads

Base.metadata.create_all(bind=engine)

app = FastAPI(title="CLAIRO API")

def _rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"error": "Rate limit exceeded. Please slow down and try again shortly."},
    )


app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


@app.middleware("http")
async def reject_oversized_bodies(request: Request, call_next):
    """Cheap defense-in-depth against huge JSON payloads on endpoints that
    don't do their own size check (multipart file uploads enforce their own
    limits inside the route instead, since the body has to be streamed)."""
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit():
        if int(content_length) > MAX_JSON_BODY_BYTES and "multipart" not in (
            request.headers.get("content-type") or ""
        ):
            return JSONResponse(status_code=413, content={"error": "Request body too large."})
    return await call_next(request)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# Allow requests from the Vite dev server (and any localhost port), plus any
# production frontend origins supplied via the CORS_ORIGINS env var
# (comma-separated, e.g. "https://clairo.vercel.app,https://app.clairo.com").
_default_origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:3000",
]
_extra_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_default_origins + _extra_origins,
    # Also allow common deployment subdomains (Vercel/Netlify/Render previews)
    # so a freshly deployed frontend works without redeploying the backend.
    # Safe to combine with a broad regex like this because allow_credentials
    # is False below — CLAIRO's frontend never sends cookies, so there's no
    # session/credential leakage risk from a shared-hosting subdomain match.
    allow_origin_regex=r"https://.*\.(vercel|netlify|onrender|railway)\.app",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router)
app.include_router(rag_router, prefix="/rag")
app.include_router(appeal_router, prefix="/appeal")
app.include_router(risk_router, prefix="/risk")
app.include_router(export_router, prefix="/export")
app.include_router(analytics_router, prefix="/analytics")
app.include_router(voice_router, prefix="/voice")
app.include_router(prior_auth_router, prefix="/api")

# Alias without /api prefix for clients calling /prior-auth-check-documents directly
app.post("/prior-auth-check-documents")(prior_auth_check_documents)
app.include_router(insforge_router, prefix="/insforge")

@app.get("/")
def root():
    return {"message": "CLAIRO backend is running", "db": "InsForge Postgres"}
