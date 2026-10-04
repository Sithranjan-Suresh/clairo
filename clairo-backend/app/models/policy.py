from sqlalchemy import Column, DateTime, Integer, String

from app.database import Base
from app.models.base import utcnow


class PayerPolicy(Base):
    """Catalog of the policy PDFs indexed in the vector store (synced at startup)."""

    __tablename__ = "payer_policies"

    id = Column(Integer, primary_key=True)
    payer = Column(String(100), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    source_file = Column(String(500), nullable=False, unique=True)
    chunk_count = Column(Integer, nullable=False, default=0)
    synced_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
