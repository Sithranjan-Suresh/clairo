from sqlalchemy import func, case
from app.database import SessionLocal
from app.models import DenialClaim
from collections import defaultdict


# Industry benchmark averages for specialty practices
INDUSTRY_BENCHMARKS = {
    "denial_rate": 11.8,
    "appeal_overturn_rate": 63.0,
    "avg_days_to_appeal": 18.0,
}

AVG_REVENUE_PER_CLAIM = 3800  # realistic average for specialty


def get_denials_by_payer():
    db = SessionLocal()
    try:
        results = (
            db.query(DenialClaim.payer, func.count(DenialClaim.id).label("count"))
            .group_by(DenialClaim.payer)
            .order_by(func.count(DenialClaim.id).desc())
            .all()
        )
        return [{"payer": r.payer, "denial_count": r.count} for r in results]
    finally:
        db.close()


def get_denials_by_cpt():
    db = SessionLocal()
    try:
        results = (
            db.query(DenialClaim.cpt_codes, func.count(DenialClaim.id).label("count"))
            .group_by(DenialClaim.cpt_codes)
            .order_by(func.count(DenialClaim.id).desc())
            .all()
        )
        return [{"cpt_code": r.cpt_codes, "denial_count": r.count} for r in results]
    finally:
        db.close()


def get_denials_by_classification():
    db = SessionLocal()
    try:
        results = (
            db.query(DenialClaim.classification, func.count(DenialClaim.id).label("count"))
            .group_by(DenialClaim.classification)
            .order_by(func.count(DenialClaim.id).desc())
            .all()
        )
        total = sum(r.count for r in results)
        return [
            {
                "classification": r.classification,
                "count": r.count,
                "percentage": round((r.count / total) * 100, 1) if total > 0 else 0
            }
            for r in results
        ]
    finally:
        db.close()


def get_denials_by_month():
    db = SessionLocal()
    try:
        results = db.query(DenialClaim.created_at).all()
        monthly = defaultdict(int)
        for r in results:
            if r.created_at:
                month = r.created_at[:7]  # "YYYY-MM"
                monthly[month] += 1
        sorted_months = sorted(monthly.items())
        return [{"month": m, "denial_count": c} for m, c in sorted_months]
    finally:
        db.close()


def get_summary_stats():
    db = SessionLocal()
    try:
        total_claims = db.query(func.count(DenialClaim.id)).scalar()
        appeals_generated = db.query(func.count(DenialClaim.id)).filter(
            DenialClaim.appeal_generated == 1
        ).scalar()
        avg_risk = db.query(func.avg(DenialClaim.risk_score)).scalar()

        # Estimate total denied revenue
        total_denied_revenue = total_claims * AVG_REVENUE_PER_CLAIM

        # Practice denial rate (simulated — in production this comes from total submitted claims)
        practice_denial_rate = round(14.2, 1)  # demo value, realistically above industry avg
        industry_denial_rate = INDUSTRY_BENCHMARKS["denial_rate"]

        # Excess denial cost vs industry average
        excess_denial_rate = practice_denial_rate - industry_denial_rate
        excess_claims = int((excess_denial_rate / 100) * total_claims * 10)  # estimate
        excess_revenue_loss = excess_claims * AVG_REVENUE_PER_CLAIM

        return {
            "total_denials_processed": total_claims,
            "appeals_generated": appeals_generated,
            "appeal_rate": round((appeals_generated / total_claims * 100), 1) if total_claims > 0 else 0,
            "avg_risk_score": round(avg_risk, 1) if avg_risk else 0,
            "total_denied_revenue": f"${total_denied_revenue:,}",
            "practice_denial_rate": f"{practice_denial_rate}%",
            "industry_denial_rate": f"{industry_denial_rate}%",
            "benchmark_gap": f"+{round(excess_denial_rate, 1)}%",
            "excess_annual_loss": f"${excess_revenue_loss:,}",
        }
    finally:
        db.close()