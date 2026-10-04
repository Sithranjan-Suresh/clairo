from typing import Optional

from fastapi import Request
from sqlalchemy.orm import Session

from app.observability import client_ip, request_id_var
from app.repositories import audit as audit_repo


def record(
    db: Session,
    action: str,
    *,
    user=None,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    details: Optional[dict] = None,
    request: Optional[Request] = None,
    actor_email: Optional[str] = None,
):
    """Add an audit row to the caller's transaction (the caller commits, so the
    audit entry and the change it describes succeed or fail together)."""
    entry = audit_repo.add(
        db,
        action=action,
        user=user,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
        ip_address=client_ip(request) if request is not None else None,
        request_id=request_id_var.get(),
    )
    if user is None and actor_email:
        entry.actor_email = actor_email
    return entry
