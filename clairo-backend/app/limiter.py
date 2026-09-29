"""Shared rate limiter instance.

Kept in its own module (rather than app.main) so route modules can import
it without a circular import back to main.py, which is where it gets
wired into the FastAPI app (state, middleware, exception handler).

In-memory storage is fine for a single-process deployment (Render/Railway
free-tier style). If CLAIRO is ever scaled to multiple worker processes or
instances, point this at Redis instead — see slowapi's `storage_uri`.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
