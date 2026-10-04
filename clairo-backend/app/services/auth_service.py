import logging
from typing import Optional

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from app.config import ADMIN_EMAIL, ADMIN_PASSWORD, ALLOW_REGISTRATION
from app.models import User
from app.models.user import ROLE_ADMIN, ROLE_USER
from app.repositories import users as users_repo
from app.security.auth import create_access_token, hash_password, verify_password
from app.services import audit_service

logger = logging.getLogger(__name__)

# Verified against when the email is unknown, so "no such user" and "wrong
# password" take the same time (no account-enumeration timing signal).
_DUMMY_HASH = hash_password("clairo-dummy-password")


def register(db: Session, email: str, password: str, request: Optional[Request] = None) -> User:
    if not ALLOW_REGISTRATION:
        raise HTTPException(status_code=403, detail="Registration is disabled.")
    if users_repo.get_by_email(db, email):
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    user = users_repo.create(db, email, hash_password(password), ROLE_USER)
    audit_service.record(db, "auth.register", user=user, entity_type="user",
                         entity_id=user.id, request=request)
    db.commit()
    return user


def authenticate(db: Session, email: str, password: str, request: Optional[Request] = None) -> User:
    user = users_repo.get_by_email(db, email)
    ok = verify_password(password, user.password_hash if user else _DUMMY_HASH)
    if not user or not ok or not user.is_active:
        audit_service.record(db, "auth.login_failed", actor_email=email.strip().lower()[:255],
                             details={"reason": "bad_credentials"}, request=request)
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    audit_service.record(db, "auth.login", user=user, entity_type="user",
                         entity_id=user.id, request=request)
    db.commit()
    return user


def issue_token(user: User) -> str:
    return create_access_token(user)


def bootstrap_admin(db: Session) -> Optional[User]:
    """Create/refresh the admin account from ADMIN_EMAIL / ADMIN_PASSWORD.

    This is the only way to obtain an admin: self-registration always yields a
    plain user, so a public deployment can't be talked into minting admins.
    """
    if not ADMIN_EMAIL or not ADMIN_PASSWORD:
        return None
    user = users_repo.get_by_email(db, ADMIN_EMAIL)
    if user is None:
        user = users_repo.create(db, ADMIN_EMAIL, hash_password(ADMIN_PASSWORD), ROLE_ADMIN)
        logger.info("bootstrapped admin account %s", ADMIN_EMAIL)
    else:
        user.role = ROLE_ADMIN
        user.is_active = True
        if not verify_password(ADMIN_PASSWORD, user.password_hash):
            user.password_hash = hash_password(ADMIN_PASSWORD)
    db.commit()
    return user
