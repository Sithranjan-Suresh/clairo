from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AuditLog


def add(
    db: Session,
    *,
    action: str,
    user=None,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None,
    request_id: Optional[str] = None,
) -> AuditLog:
    entry = AuditLog(
        user_id=getattr(user, "id", None),
        actor_email=getattr(user, "email", None),
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
        ip_address=ip_address,
        request_id=request_id,
    )
    db.add(entry)
    db.flush()
    return entry


def list_logs(
    db: Session,
    *,
    action: Optional[str] = None,
    user_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
):
    query = select(AuditLog)
    count_query = select(func.count(AuditLog.id))
    if action:
        query = query.where(AuditLog.action == action)
        count_query = count_query.where(AuditLog.action == action)
    if user_id:
        query = query.where(AuditLog.user_id == user_id)
        count_query = count_query.where(AuditLog.user_id == user_id)
    total = db.scalar(count_query) or 0
    rows = db.scalars(
        query.order_by(AuditLog.id.desc()).limit(limit).offset(offset)
    ).all()
    return rows, total


def for_claim(db: Session, claim_id: int):
    """Everything that happened to a claim, oldest first (appeal events are
    logged against the claim too, so one query covers the whole history)."""
    return db.scalars(
        select(AuditLog)
        .where(AuditLog.entity_type == "claim", AuditLog.entity_id == claim_id)
        .order_by(AuditLog.id.asc())
    ).all()
