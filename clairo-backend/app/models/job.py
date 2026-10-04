from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, Integer, String, Text

from app.database import Base
from app.models.base import utcnow

JOB_QUEUED = "queued"
JOB_RUNNING = "running"
JOB_SUCCEEDED = "succeeded"
JOB_FAILED = "failed"


class Job(Base):
    """Postgres-backed work queue row (claimed with FOR UPDATE SKIP LOCKED)."""

    __tablename__ = "jobs"

    id = Column(String(32), primary_key=True)          # uuid4 hex
    type = Column(String(40), nullable=False)
    status = Column(String(12), nullable=False, default=JOB_QUEUED)
    claim_id = Column(Integer, ForeignKey("denial_claims.id", ondelete="CASCADE"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    payload = Column(JSON, nullable=True)
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    attempts = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=3)
    run_after = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (Index("ix_jobs_status_run_after", "status", "run_after"),)
