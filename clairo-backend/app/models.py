from sqlalchemy import Column, Integer, String, Text, Float, Date
from app.database import Base


class DenialClaim(Base):
    __tablename__ = "denial_claims"

    id = Column(Integer, primary_key=True, index=True)
    payer = Column(String, nullable=True)
    patient_id = Column(String, nullable=True)
    cpt_codes = Column(String, nullable=True)        # stored as comma-separated string
    denial_reason = Column(String, nullable=True)
    classification = Column(String, nullable=True)
    billed_amount = Column(String, nullable=True)
    denied_amount = Column(String, nullable=True)
    service_date = Column(String, nullable=True)
    risk_score = Column(Float, nullable=True)
    appeal_generated = Column(Integer, default=0)   # 0 or 1
    created_at = Column(String, nullable=True)