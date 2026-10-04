from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import utcnow

STATUS_UPLOADED = "uploaded"
STATUS_ANALYZING = "analyzing"
STATUS_ANALYZED = "analyzed"
STATUS_APPEALED = "appealed"
STATUS_FAILED = "failed"
CLAIM_STATUSES = (
    STATUS_UPLOADED, STATUS_ANALYZING, STATUS_ANALYZED, STATUS_APPEALED, STATUS_FAILED,
)


class DenialClaim(Base):
    """A denied claim.

    The table keeps its original name (denial_claims) so the data already in
    production survives. Rows with user_id NULL are the shared demo data.
    """

    __tablename__ = "denial_claims"

    id = Column(Integer, primary_key=True, index=True)
    # Legacy columns. String-typed amounts/dates are a known schema smell.
    payer = Column(String, nullable=True)
    patient_id = Column(String, nullable=True)
    cpt_codes = Column(String, nullable=True)        # comma-separated
    denial_reason = Column(String, nullable=True)
    classification = Column(String, nullable=True)
    billed_amount = Column(String, nullable=True)
    denied_amount = Column(String, nullable=True)
    service_date = Column(String, nullable=True)
    risk_score = Column(Float, nullable=True)
    appeal_generated = Column(Integer, default=0)    # 0 or 1
    created_at = Column(String, nullable=True)       # YYYY-MM-DD
    # Added in migration 0002.
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(20), nullable=False, default=STATUS_ANALYZED,
                    server_default=STATUS_ANALYZED)
    error_message = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True, default=utcnow, onupdate=utcnow)

    owner = relationship("User", back_populates="claims")
    documents = relationship("Document", back_populates="claim", cascade="all, delete-orphan")
    appeals = relationship("Appeal", back_populates="claim", cascade="all, delete-orphan",
                           order_by="Appeal.id.desc()")
    risk_scores = relationship("RiskScore", back_populates="claim", cascade="all, delete-orphan",
                               order_by="RiskScore.id.desc()")

    __table_args__ = (
        Index("ix_claims_payer", "payer"),
        Index("ix_claims_classification", "classification"),
        Index("ix_claims_risk_score", "risk_score"),
        Index("ix_claims_status", "status"),
        Index("ix_claims_user_id_id", "user_id", "id"),
    )

    @property
    def cpt_list(self) -> list:
        return [c.strip() for c in (self.cpt_codes or "").split(",") if c.strip()]
