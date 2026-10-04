import random
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.limiter import limiter
from app.models import DenialClaim, User
from app.security.auth import get_current_user, require_admin_or_key
from app.services import audit_service
from app.services.analytics_service import (
    get_denials_by_classification,
    get_denials_by_cpt,
    get_denials_by_month,
    get_denials_by_payer,
    get_summary_stats,
)

router = APIRouter(tags=["analytics"])


@router.post("/seed")
@limiter.limit("3/minute")
def seed_demo_data(
    request: Request,
    force: bool = False,
    db: Session = Depends(get_db),
    admin: Optional[User] = Depends(require_admin_or_key),
):
    """Wipe + reseed the *shared demo* claims (user_id NULL). Real users'
    claims are never touched. Admin JWT or X-Admin-Key only."""
    demo = DenialClaim.user_id.is_(None)
    existing = db.scalar(select(func.count(DenialClaim.id)).where(demo)) or 0
    if existing > 0 and not force:
        return {"message": f"Already seeded with {existing} claims. Pass ?force=true to reseed."}

    db.execute(delete(DenialClaim).where(demo))

    payers = ["UHC", "Aetna", "BCBS", "Cigna", "Humana"]
    classifications = [
        "medical_necessity", "prior_authorization", "coding_mismatch",
        "eligibility", "documentation_gap", "timely_filing",
    ]
    cpt_pool = ["29881", "27447", "93306", "70553", "43239", "22612", "29880"]
    payer_weights = [0.30, 0.25, 0.20, 0.15, 0.10]
    base_date = datetime(2026, 1, 1)

    claims = []
    for i in range(120):
        payer = random.choices(payers, weights=payer_weights)[0]
        classification = random.choices(
            classifications, weights=[0.35, 0.20, 0.15, 0.10, 0.15, 0.05]
        )[0]
        service_date = base_date + timedelta(days=random.randint(0, 170))
        billed = random.choice([2400, 3200, 4200, 5800, 7500, 12000])
        appealed = random.choice([0, 1])
        claims.append(DenialClaim(
            payer=payer,
            patient_id=f"P{10000 + i}",
            cpt_codes=random.choice(cpt_pool),
            denial_reason=classification.replace("_", " ").title(),
            classification=classification,
            billed_amount=f"${billed}",
            denied_amount=f"${billed}",
            service_date=service_date.strftime("%Y-%m-%d"),
            risk_score=random.randint(20, 95),
            appeal_generated=appealed,
            status="appealed" if appealed else "analyzed",
            created_at=service_date.strftime("%Y-%m-%d"),
            user_id=None,
        ))
    db.add_all(claims)
    audit_service.record(db, "admin.seed_demo_data", user=admin, details={"count": len(claims)},
                         request=request, actor_email=None if admin else "admin-api-key")
    db.commit()
    return {"message": "Successfully seeded 120 demo claims."}


@router.get("/by-payer")
def denials_by_payer(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return get_denials_by_payer(db, user)


@router.get("/by-cpt")
def denials_by_cpt(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return get_denials_by_cpt(db, user)


@router.get("/by-classification")
def denials_by_classification(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return get_denials_by_classification(db, user)


@router.get("/by-month")
def denials_by_month(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return get_denials_by_month(db, user)


@router.get("/summary")
def summary_stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return get_summary_stats(db, user)
