from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import User


def get(db: Session, user_id: int) -> Optional[User]:
    return db.get(User, user_id)


def get_by_email(db: Session, email: str) -> Optional[User]:
    return db.scalar(select(User).where(User.email == email.strip().lower()))


def create(db: Session, email: str, password_hash: str, role: str) -> User:
    user = User(email=email.strip().lower(), password_hash=password_hash, role=role)
    db.add(user)
    db.flush()
    return user


def count(db: Session) -> int:
    return db.scalar(select(func.count(User.id))) or 0
