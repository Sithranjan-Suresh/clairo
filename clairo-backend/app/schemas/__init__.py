import re
from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, field_validator

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class _ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- auth ---------------------------------------------------------------------
class RegisterRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        v = v.strip().lower()
        if len(v) > 255 or not _EMAIL_RE.match(v):
            raise ValueError("Enter a valid email address.")
        return v

    @field_validator("password")
    @classmethod
    def _password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters.")
        if len(v) > 128:
            raise ValueError("Password must be at most 128 characters.")
        return v


class LoginRequest(BaseModel):
    email: str
    password: str


class UserOut(_ORM):
    id: int
    email: str
    role: str
    created_at: Optional[datetime] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# --- claims -------------------------------------------------------------------
class RiskScoreOut(_ORM):
    id: int
    score: float
    level: str
    rule_score: int
    llm_score: int
    flags: Optional[List[str]] = None
    remediation: Optional[str] = None
    created_at: Optional[datetime] = None


class AppealOut(_ORM):
    id: int
    letter_text: str
    confidence_score: int
    confidence_rationale: Optional[str] = None
    citations: Optional[List[Any]] = None
    model: Optional[str] = None
    created_at: Optional[datetime] = None


class DocumentOut(_ORM):
    id: int
    original_filename: Optional[str] = None
    size_bytes: int
    sha256: str
    created_at: Optional[datetime] = None


class ClaimSummary(BaseModel):
    id: int
    payer: Optional[str] = None
    patient_id: Optional[str] = None
    cpt_codes: List[str] = []
    classification: Optional[str] = None
    risk_score: Optional[float] = None
    risk_level: str = "LOW"
    status: str
    appeal_generated: bool = False
    billed_amount: Optional[str] = None
    denied_amount: Optional[str] = None
    service_date: Optional[str] = None
    created_at: Optional[str] = None
    is_demo: bool = False


class ClaimDetail(ClaimSummary):
    denial_reason: Optional[str] = None
    error_message: Optional[str] = None
    owner_id: Optional[int] = None
    documents: List[DocumentOut] = []
    risk_history: List[RiskScoreOut] = []
    appeals: List[AppealOut] = []


class Page(BaseModel):
    items: List[Any]
    total: int
    limit: int
    offset: int


class JobOut(BaseModel):
    id: str
    type: str
    status: str
    claim_id: Optional[int] = None
    attempts: int
    error: Optional[str] = None
    result: Optional[dict] = None
    created_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class AuditOut(_ORM):
    id: int
    actor_email: Optional[str] = None
    action: str
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    details: Optional[dict] = None
    ip_address: Optional[str] = None
    request_id: Optional[str] = None
    created_at: Optional[datetime] = None


class PolicyOut(_ORM):
    id: int
    payer: str
    title: str
    source_file: str
    chunk_count: int
