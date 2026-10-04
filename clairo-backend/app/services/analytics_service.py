from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import DenialClaim, User
from app.repositories.claims import visibility_clause

# Industry benchmark averages for specialty practices
INDUSTRY_BENCHMARKS = {
    "denial_rate": 11.8,
    "appeal_overturn_rate": 63.0,
    "avg_days_to_appeal": 18.0,
}

AVG_REVENUE_PER_CLAIM = 3800  # illustrative average for specialty practices


def _scope(user: User) -> list:
    clause = visibility_clause(user)
    return [] if clause is None else [clause]


def get_denials_by_payer(db: Session, user: User):
    rows = db.execute(
        select(DenialClaim.payer, func.count(DenialClaim.id).label("count"))
        .where(*_scope(user))
        .group_by(DenialClaim.payer)
        .order_by(func.count(DenialClaim.id).desc())
    ).all()
    return [{"payer": r.payer, "denial_count": r.count} for r in rows]


def get_denials_by_cpt(db: Session, user: User):
    """Denial counts per individual CPT code.

    cpt_codes is stored as a comma-separated string per claim (e.g.
    "29881, 29880"), so grouping on the raw column treats every distinct
    code combination as its own bucket. We explode and recount instead.
    """
    rows = db.execute(
        select(DenialClaim.cpt_codes)
        .where(DenialClaim.cpt_codes.isnot(None), *_scope(user))
    ).all()
    counts = defaultdict(int)
    for (raw,) in rows:
        if not raw:
            continue
        for code in raw.split(","):
            code = code.strip()
            if code:
                counts[code] += 1
    return sorted(
        [{"cpt_code": code, "denial_count": n} for code, n in counts.items()],
        key=lambda item: item["denial_count"],
        reverse=True,
    )


def get_denials_by_classification(db: Session, user: User):
    rows = db.execute(
        select(DenialClaim.classification, func.count(DenialClaim.id).label("count"))
        .where(*_scope(user))
        .group_by(DenialClaim.classification)
        .order_by(func.count(DenialClaim.id).desc())
    ).all()
    total = sum(r.count for r in rows)
    return [
        {
            "classification": r.classification,
            "count": r.count,
            "percentage": round((r.count / total) * 100, 1) if total > 0 else 0,
        }
        for r in rows
    ]


def get_denials_by_month(db: Session, user: User):
    rows = db.execute(
        select(DenialClaim.created_at).where(DenialClaim.created_at.isnot(None), *_scope(user))
    ).all()
    monthly = defaultdict(int)
    for (created,) in rows:
        monthly[created[:7]] += 1   # "YYYY-MM"
    return [{"month": m, "denial_count": c} for m, c in sorted(monthly.items())]


def get_summary_stats(db: Session, user: User):
    scope = _scope(user)
    total_claims = db.scalar(select(func.count(DenialClaim.id)).where(*scope)) or 0
    appeals_generated = db.scalar(
        select(func.count(DenialClaim.id)).where(DenialClaim.appeal_generated == 1, *scope)
    ) or 0
    avg_risk = db.scalar(select(func.avg(DenialClaim.risk_score)).where(*scope))

    total_denied_revenue = total_claims * AVG_REVENUE_PER_CLAIM

    # Practice denial rate is illustrative: true rate needs total *submitted*
    # claim volume, which CLAIRO doesn't track.
    practice_denial_rate = 14.2
    industry_denial_rate = INDUSTRY_BENCHMARKS["denial_rate"]
    excess_denial_rate = practice_denial_rate - industry_denial_rate
    excess_claims = int((excess_denial_rate / 100) * total_claims * 10)
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
