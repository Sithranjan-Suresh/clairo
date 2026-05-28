from fastapi import APIRouter
from app.services.analytics_service import (
    get_denials_by_payer,
    get_denials_by_cpt,
    get_denials_by_classification,
    get_denials_by_month,
    get_summary_stats
)
from app.database import SessionLocal, Base, engine
from app.models import DenialClaim
import random
from datetime import datetime, timedelta

router = APIRouter()


@router.post("/seed")
def seed_demo_data():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Don't re-seed if data already exists
    existing = db.query(DenialClaim).count()
    if existing > 0:
        db.close()
        return {"message": f"Already seeded with {existing} claims, skipping."}

    payers = ["UHC", "Aetna", "BCBS", "Cigna", "Humana"]
    classifications = [
        "medical_necessity",
        "prior_authorization",
        "coding_mismatch",
        "eligibility",
        "documentation_gap",
        "timely_filing"
    ]
    cpt_pool = [
        "29881", "27447", "93306",
        "70553", "43239", "22612", "29880"
    ]
    payer_weights = [0.30, 0.25, 0.20, 0.15, 0.10]
    base_date = datetime(2026, 1, 1)
    claims = []

    for i in range(120):
        payer = random.choices(payers, weights=payer_weights)[0]
        cpt = random.choice(cpt_pool)
        classification = random.choices(
            classifications,
            weights=[0.35, 0.20, 0.15, 0.10, 0.15, 0.05]
        )[0]
        service_date = base_date + timedelta(days=random.randint(0, 170))
        risk_score = random.randint(20, 95)
        billed = random.choice([2400, 3200, 4200, 5800, 7500, 12000])

        claims.append(DenialClaim(
            payer=payer,
            patient_id=f"P{10000 + i}",
            cpt_codes=cpt,
            denial_reason=classification.replace("_", " ").title(),
            classification=classification,
            billed_amount=f"${billed}",
            denied_amount=f"${billed}",
            service_date=service_date.strftime("%Y-%m-%d"),
            risk_score=risk_score,
            appeal_generated=random.choice([0, 1]),
            created_at=service_date.strftime("%Y-%m-%d")
        ))

    db.add_all(claims)
    db.commit()
    db.close()

    return {"message": f"Successfully seeded 120 demo claims."}


@router.get("/by-payer")
def denials_by_payer():
    return get_denials_by_payer()


@router.get("/by-cpt")
def denials_by_cpt():
    return get_denials_by_cpt()


@router.get("/by-classification")
def denials_by_classification():
    return get_denials_by_classification()


@router.get("/by-month")
def denials_by_month():
    return get_denials_by_month()


@router.get("/summary")
def summary_stats():
    return get_summary_stats()