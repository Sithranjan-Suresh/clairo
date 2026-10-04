from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import utcnow


class RiskScore(Base):
    """Every scoring run is kept (not overwritten) so score history is auditable."""

    __tablename__ = "risk_scores"

    id = Column(Integer, primary_key=True)
    claim_id = Column(Integer, ForeignKey("denial_claims.id", ondelete="CASCADE"),
                      nullable=False, index=True)
    score = Column(Float, nullable=False)
    level = Column(String(10), nullable=False)
    rule_score = Column(Integer, nullable=False, default=0)
    llm_score = Column(Integer, nullable=False, default=0)
    flags = Column(JSON, nullable=True)
    remediation = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    claim = relationship("DenialClaim", back_populates="risk_scores")
