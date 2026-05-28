import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.database import engine, SessionLocal, Base
from app.models import DenialClaim
from datetime import datetime, timedelta
import random

Base.metadata.create_all(bind=engine)

db = SessionLocal()

# Clear existing data
db.query(DenialClaim).delete()
db.commit()

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
    ("29881", "Knee Arthroscopy"),
    ("27447", "Total Knee Replacement"),
    ("93306", "Echocardiography"),
    ("70553", "Brain MRI"),
    ("43239", "Upper GI Endoscopy"),
    ("22612", "Spinal Fusion"),
    ("29880", "Knee Meniscectomy"),
]

# Weights to make UHC and Aetna the most common deniers
payer_weights = [0.30, 0.25, 0.20, 0.15, 0.10]

# Generate 6 months of realistic claim data
claims = []
base_date = datetime(2026, 1, 1)

for i in range(120):
    payer = random.choices(payers, weights=payer_weights)[0]
    cpt, _ = random.choice(cpt_pool)
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

print(f"Seeded {len(claims)} demo claims successfully.")