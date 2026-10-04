"""Shared rate limiter instance.

Kept in its own module so route modules can import it without a circular
import back to main.py, where it is wired into the app.

Identity: authenticated requests are limited per *user* (so one noisy user
can't burn a whole office's quota behind a shared IP); anonymous ones per
client IP. Storage is in-memory by default and switches to Redis when
REDIS_URL is set, which makes the limits hold across multiple instances.
"""
from slowapi import Limiter
from starlette.requests import Request

from app.config import REDIS_URL
from app.observability import client_ip
from app.security.auth import token_subject


def rate_limit_key(request: Request) -> str:
    sub = token_subject(request)
    return f"user:{sub}" if sub else f"ip:{client_ip(request)}"


limiter = Limiter(
    key_func=rate_limit_key,
    default_limits=["120/minute"],
    storage_uri=REDIS_URL or "memory://",
    in_memory_fallback_enabled=bool(REDIS_URL),  # Redis outage must not take the API down
    swallow_errors=True,
)
