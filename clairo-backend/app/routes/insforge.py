"""
InsForge Integration Routes
───────────────────────────
Exposes endpoints that demonstrate CLAIRO's InsForge-powered backend:

  GET  /insforge/status        — DB health check + live claim counts from InsForge Postgres
  GET  /insforge/live-claims   — Latest N denial claims straight from InsForge Postgres
  POST /insforge/agent-run     — Agent that queries InsForge Postgres for live context and
                                 synthesizes denial intelligence from it.

All reads are scoped to the caller: a user sees their own claims plus the shared
demo data; admins see everything.
"""
import json
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import DATABASE_URL
from app.database import get_db
from app.limiter import limiter
from app.models import DenialClaim, User
from app.repositories.claims import risk_level, visibility_clause
from app.security.auth import get_current_user
from app.services.groq_services import CHAT_MODEL, client

router = APIRouter()


def _scope(user: User) -> list:
    clause = visibility_clause(user)
    return [] if clause is None else [clause]


@router.get("/status")
def insforge_status(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Confirms InsForge Postgres is reachable and returns live claim stats."""
    is_insforge = DATABASE_URL.startswith("postgresql")
    backend = "InsForge Postgres" if is_insforge else "SQLite (local fallback)"
    scope = _scope(user)
    try:
        t0 = time.time()
        total = db.scalar(select(func.count(DenialClaim.id)).where(*scope)) or 0
        high_risk = db.scalar(
            select(func.count(DenialClaim.id)).where(DenialClaim.risk_score >= 70, *scope)
        ) or 0
        appeals = db.scalar(
            select(func.count(DenialClaim.id)).where(DenialClaim.appeal_generated == 1, *scope)
        ) or 0
        query_ms = round((time.time() - t0) * 1000, 1)
        return {
            "backend": backend,
            "insforge_connected": is_insforge,
            "status": "healthy",
            "query_latency_ms": query_ms,
            "live_stats": {
                "total_claims": total,
                "high_risk_claims": high_risk,
                "appeals_generated": appeals,
                "appeal_rate_pct": round(appeals / total * 100, 1) if total else 0,
            },
        }
    except Exception:
        return {"backend": backend, "insforge_connected": is_insforge,
                "status": "error", "error": "Database query failed."}


@router.get("/live-claims")
def insforge_live_claims(
    limit: int = 20, db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    """Most recent claims, newest first (the live feed in the InsForge tab)."""
    rows = db.scalars(
        select(DenialClaim).where(*_scope(user)).order_by(DenialClaim.id.desc())
        .limit(max(1, min(limit, 100)))
    ).all()
    return {
        "claims": [
            {
                "id": r.id,
                "payer": r.payer or "—",
                "patient_id": r.patient_id or "—",
                "cpt_codes": r.cpt_codes or "—",
                "classification": r.classification or "—",
                "risk_score": r.risk_score,
                "risk_level": risk_level(r.risk_score),
                "appeal_generated": bool(r.appeal_generated),
                "service_date": r.service_date or "—",
                "created_at": r.created_at or "—",
            }
            for r in rows
        ],
        "total_returned": len(rows),
    }


class AgentRunRequest(BaseModel):
    query: str
    payer: Optional[str] = None
    cpt_codes: Optional[list[str]] = None


@router.post("/agent-run")
@limiter.limit("10/minute")
def insforge_agent_run(
    request: Request,
    payload: AgentRunRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Query InsForge for live context, then have the LLM answer from it."""
    scope = _scope(user)
    total_claims = db.scalar(select(func.count(DenialClaim.id)).where(*scope)) or 0

    payer_filter = payload.payer
    payer_stats = None
    if payer_filter:
        count = db.scalar(
            select(func.count(DenialClaim.id)).where(DenialClaim.payer == payer_filter, *scope)
        ) or 0
        avg_risk = db.scalar(
            select(func.avg(DenialClaim.risk_score)).where(DenialClaim.payer == payer_filter, *scope)
        )
        payer_stats = {
            "payer": payer_filter,
            "total_denials": count,
            "avg_risk_score": round(float(avg_risk), 1) if avg_risk else None,
        }

    q = select(DenialClaim).where(DenialClaim.risk_score >= 70, *scope)
    if payer_filter:
        q = q.where(DenialClaim.payer == payer_filter)
    recent_high_risk = db.scalars(q.order_by(DenialClaim.id.desc()).limit(5)).all()

    high_risk_context = [
        {
            "id": r.id, "payer": r.payer, "cpt_codes": r.cpt_codes,
            "classification": r.classification, "risk_score": r.risk_score,
            "denial_reason": r.denial_reason,
        }
        for r in recent_high_risk
    ]

    db_context_str = json.dumps({
        "total_claims_in_insforge_db": total_claims,
        "payer_stats": payer_stats,
        "recent_high_risk_claims": high_risk_context,
        "cpt_codes_of_interest": payload.cpt_codes,
    }, indent=2)

    prompt = f"""You are CLAIRO's autonomous denial intelligence agent.
You have live access to InsForge Postgres (CLAIRO's cloud database) and you've
just queried it for context. Use that data to answer the user's question.

USER QUERY: {payload.query}

LIVE DATA FROM INSFORGE POSTGRES:
{db_context_str}

Instructions:
- Answer the user's question using the live InsForge data
- Be specific: cite claim counts, risk scores, and payer names from the data
- If the data is sparse (few claims), say so and explain what it will show at scale
- End with one concrete action recommendation for the practice
- Keep your response under 300 words, structured, professional

Return ONLY valid JSON:
{{
  "summary": "<2-3 sentence direct answer citing the InsForge data>",
  "key_findings": ["<finding 1>", "<finding 2>", "<finding 3>"],
  "recommendation": "<one concrete action>",
  "data_source": "InsForge Postgres — live query"
}}"""

    try:
        response = client.chat.completions.create(
            model=CHAT_MODEL,
            task="insforge_agent",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        raw = response.choices[0].message.content.strip()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Agent synthesis failed: {exc}") from exc

    raw = raw.replace("```json", "").replace("```", "").strip()
    try:
        agent_output = json.loads(raw)
    except Exception:
        agent_output = {
            "summary": raw[:400],
            "key_findings": [],
            "recommendation": "",
            "data_source": "InsForge Postgres — live query",
        }

    return {
        "query": payload.query,
        "insforge_context": {
            "total_claims": total_claims,
            "payer_stats": payer_stats,
            "high_risk_claims_sampled": len(high_risk_context),
        },
        "agent_response": agent_output,
    }
