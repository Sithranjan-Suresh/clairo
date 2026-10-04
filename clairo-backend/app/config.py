"""Central, typed access to environment configuration.

Everything reads from env vars at import time so tests can set them before
importing the app (see tests/conftest.py).
"""
import logging
import os
import secrets

from dotenv import load_dotenv

load_dotenv()  # must run before any os.getenv below

logger = logging.getLogger(__name__)


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _database_url() -> str:
    url = os.getenv("DATABASE_URL") or os.getenv("INSFORGE_DATABASE_URL")
    if not url:
        return "sqlite:///./clairo.db"
    # Some providers hand out the legacy "postgres://" scheme, which
    # SQLAlchemy 2.x no longer accepts.
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    return url


DATABASE_URL = _database_url()
IS_POSTGRES = DATABASE_URL.startswith("postgresql")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# --- auth -----------------------------------------------------------------
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "720"))
_jwt_secret = os.getenv("JWT_SECRET")
if not _jwt_secret:
    # Fail-soft: an ephemeral secret keeps the app usable, but every restart
    # invalidates all sessions, and it's wrong for multi-instance setups.
    _jwt_secret = secrets.token_urlsafe(48)
    logger.critical(
        "JWT_SECRET is not set — using an ephemeral secret. All logins will be "
        "invalidated on restart. Set JWT_SECRET in production."
    )
JWT_SECRET = _jwt_secret

ADMIN_EMAIL = (os.getenv("ADMIN_EMAIL") or "").strip().lower()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD") or ""
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY") or ""
ALLOW_REGISTRATION = _bool("ALLOW_REGISTRATION", True)

# --- infrastructure ---------------------------------------------------------
REDIS_URL = os.getenv("REDIS_URL") or ""
AUTO_MIGRATE = _bool("AUTO_MIGRATE", True)
WORKER_ENABLED = _bool("WORKER_ENABLED", True)
WORKER_POLL_SECONDS = float(os.getenv("WORKER_POLL_SECONDS", "1.0"))
JOB_MAX_ATTEMPTS = int(os.getenv("JOB_MAX_ATTEMPTS", "3"))

CACHE_TTL_RETRIEVAL = int(os.getenv("CACHE_TTL_RETRIEVAL", "3600"))
CACHE_TTL_ANALYSIS = int(os.getenv("CACHE_TTL_ANALYSIS", str(7 * 24 * 3600)))

UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "app/uploads")
MAX_UPLOAD_BYTES = 15 * 1024 * 1024

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_JSON = _bool("LOG_JSON", True)
