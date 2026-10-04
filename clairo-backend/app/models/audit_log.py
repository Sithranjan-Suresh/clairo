from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, Integer, String

from app.database import Base
from app.models.base import utcnow


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    actor_email = Column(String(255), nullable=True)   # denormalised: survives user deletion
    action = Column(String(60), nullable=False, index=True)
    entity_type = Column(String(40), nullable=True)
    entity_id = Column(Integer, nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(64), nullable=True)
    request_id = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, index=True)

    __table_args__ = (Index("ix_audit_entity", "entity_type", "entity_id"),)
