from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import utcnow


class Appeal(Base):
    __tablename__ = "appeals"

    id = Column(Integer, primary_key=True)
    claim_id = Column(Integer, ForeignKey("denial_claims.id", ondelete="CASCADE"),
                      nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    letter_text = Column(Text, nullable=False)
    confidence_score = Column(Integer, nullable=False, default=0)
    confidence_rationale = Column(Text, nullable=True)
    citations = Column(JSON, nullable=True)   # policy chunks the letter was grounded in
    model = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    claim = relationship("DenialClaim", back_populates="appeals")
