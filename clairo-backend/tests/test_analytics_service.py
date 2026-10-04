import pytest

from app.models import DenialClaim
from app.services import analytics_service as svc


@pytest.fixture
def claims(db, user, other_user):
    def add(owner, payer, cpts, cls="medical_necessity", score=50, appealed=0, created="2026-01-15"):
        db.add(DenialClaim(
            payer=payer, cpt_codes=cpts, classification=cls, risk_score=score,
            appeal_generated=appealed, user_id=getattr(owner, "id", None),
            status="analyzed", created_at=created,
        ))

    add(user, "UHC", "29881, 29880", score=80, appealed=1)
    add(user, "UHC", "29881", cls="eligibility", score=40, created="2026-02-10")
    add(other_user, "Aetna", "93306", score=90)           # someone else's: must stay hidden
    add(None, "Cigna", "70553", score=20, created="2026-02-11")   # shared demo data
    db.commit()


def test_cpt_breakdown_counts_individual_codes_not_combinations(db, user, claims):
    result = {r["cpt_code"]: r["denial_count"] for r in svc.get_denials_by_cpt(db, user)}
    assert result == {"29881": 2, "29880": 1, "70553": 1}


def test_users_only_aggregate_their_own_and_demo_claims(db, user, claims):
    payers = {r["payer"]: r["denial_count"] for r in svc.get_denials_by_payer(db, user)}
    assert payers == {"UHC": 2, "Cigna": 1}            # no Aetna (other_user's)
    summary = svc.get_summary_stats(db, user)
    assert summary["total_denials_processed"] == 3
    assert summary["appeals_generated"] == 1
    assert summary["avg_risk_score"] == round((80 + 40 + 20) / 3, 1)


def test_admin_aggregates_everything(db, admin, claims):
    assert svc.get_summary_stats(db, admin)["total_denials_processed"] == 4
    assert {r["payer"] for r in svc.get_denials_by_payer(db, admin)} == {"UHC", "Aetna", "Cigna"}


def test_classification_percentages_sum_to_100(db, user, claims):
    rows = svc.get_denials_by_classification(db, user)
    assert round(sum(r["percentage"] for r in rows)) == 100


def test_month_trend_is_chronological(db, user, claims):
    assert svc.get_denials_by_month(db, user) == [
        {"month": "2026-01", "denial_count": 1}, {"month": "2026-02", "denial_count": 2},
    ]


def test_empty_database_is_handled(db, user):
    summary = svc.get_summary_stats(db, user)
    assert summary["total_denials_processed"] == 0 and summary["appeal_rate"] == 0
    assert svc.get_denials_by_cpt(db, user) == []
    assert svc.get_denials_by_classification(db, user) == []
