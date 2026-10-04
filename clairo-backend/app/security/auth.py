"""Password hashing, JWT issuing/verification, and FastAPI auth dependencies."""
import base64
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import ADMIN_API_KEY, JWT_ALGORITHM, JWT_EXPIRE_MINUTES, JWT_SECRET
from app.database import get_db
from app.models import User
from app.models.user import ROLE_ADMIN

_bearer = HTTPBearer(auto_error=False)


# --- passwords ----------------------------------------------------------------
def _prehash(password: str) -> bytes:
    # bcrypt only looks at the first 72 bytes (and newer releases raise on
    # longer input). Pre-hashing keeps long passphrases fully significant.
    return base64.b64encode(hashlib.sha256(password.encode("utf-8")).digest())


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prehash(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_prehash(password), password_hash.encode("utf-8"))
    except ValueError:
        return False


# --- tokens -------------------------------------------------------------------
def create_access_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "role": user.role,
        "iat": now,
        "exp": now + timedelta(minutes=JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None


def token_subject(request: Request) -> Optional[str]:
    """Cheap, DB-free user identity used by the rate limiter's key function."""
    header = request.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        payload = decode_access_token(header[7:].strip())
        if payload:
            return payload.get("sub")
    return None


# --- dependencies -------------------------------------------------------------
_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated.",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None:
        raise _UNAUTHORIZED
    payload = decode_access_token(creds.credentials)
    if not payload or not str(payload.get("sub", "")).isdigit():
        raise _UNAUTHORIZED
    user = db.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise _UNAUTHORIZED
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != ROLE_ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required.")
    return user


def _key_matches(provided: Optional[str]) -> bool:
    return bool(ADMIN_API_KEY) and bool(provided) and hmac.compare_digest(provided, ADMIN_API_KEY)


def require_admin_or_key(
    request: Request,
    x_admin_key: Optional[str] = Header(default=None),
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Admin JWT *or* the X-Admin-Key header (for curl/CI/ops scripts)."""
    if _key_matches(x_admin_key):
        return None
    if creds is not None:
        user = get_current_user(creds, db)
        if user.role == ROLE_ADMIN:
            return user
    raise HTTPException(status_code=403, detail="Admin access required.")
