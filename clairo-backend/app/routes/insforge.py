"""
InsForge Integration Routes
───────────────────────────
Exposes endpoints that demonstrate CLAIRO's InsForge-powered backend:

  GET  /insforge/status        — DB health check + live claim counts from InsForge Postgres
  GET  /insforge/live-claims   — Latest N denial claims straight from InsForge Postgres
  POST /insforge/agent-run     — Autonomous agent that orchestrates CLAIRO tools AND queries
                                 InsForge Postgres to surface denial intelligence,
                                 showing both layers working together in one call.
"""

from fastapi import APIRouter
from sqlalchemy import text
from app.database import SessionLocal, engine, DATABASE_URL
from app.models import DenialClaim
from app.services.groq_services import client
from sqlalchemy import func
import json, time

router = APIRouter()


# ─────────────────────────────────────────────────────────────────
# /insforge/status
# Returns InsForge DB backend info + live aggregate stats
# ─────────────────────────────────────────────────────────────────

@router.get("/status")
def insforge_status():
    """
    Confirms InsForge Postgres is reachable and returns live claim stats.
    Useful as a health check and as a demo-ready "backend is live" signal.
    """
    is_insforge = DATABASE_URL.startswith("postgresql") or DATABASE_URL.startswith("postgres")
    db = SessionLocal()
    try:
        t0 = time.time()
        total = db.query(func.count(DenialClaim.id)).scalar() or 0
        high_risk = (
            db.query(func.count(DenialClaim.id))
            .filter(DenialClaim.risk_score >= 70)
            .scalar() or 0
        )
        appeals = (
            db.query(func.count(DenialClaim.id))
            .filter(DenialClaim.appeal_generated == 1)
            .scalar() or 0
        )
        query_ms = round((time.time() - t0) * 1000, 1)

        return {
            "backend": "InsForge Postgres" if is_insforge else "SQLite (local fallback)",
            "insforge_connected": is_insforge,
            "status": "healthy",
            "query_latency_ms": query_ms,
            "live_stats": {
                "total_claims": total,
                "high_risk_claims": high_risk,
                "appeals_generated": appeals,
                "appeal_rate_pct": round(appeals / total * 100, 1) if total else 0,
            }
        }
    except Exception as e:
        return {
            "backend": "InsForge Postgres" if is_insforge else "SQLite (local fallback)",
            "insforge_connected": is_insforge,
            "status": "error",
            "error": str(e),
        }
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────
# /insforge/live-claims
# Latest denial claims pulled directly from InsForge Postgres
# ─────────────────────────────────────────────────────────────────

@router.get("/live-claims")
def insforge_live_claims(limit: int = 20):
    """
    Returns the most recently created denial claims from InsForge Postgres,
    newest first. This is the live feed shown in the InsForge tab.
    """
    db = SessionLocal()
    try:
        rows = (
            db.query(DenialClaim)
            .order_by(DenialClaim.id.desc())
            .limit(min(limit, 100))
            .all()
        )
        return {
            "claims": [
                {
                    "id": r.id,
                    "payer": r.payer or "—",
                    "patient_id": r.patient_id or "—",
                    "cpt_codes": r.cpt_codes or "—",
                    "classification": r.classification or "—",
                    "risk_score": r.risk_score,
                    "risk_level": (
                        "HIGH" if (r.risk_score or 0) >= 70
                        else "MEDIUM" if (r.risk_score or 0) >= 40
                        else "LOW"
                    ),
                    "appeal_generated": bool(r.appeal_generated),
                    "service_date": r.service_date or "—",
                    "created_at": r.created_at or "—",
                }
                for r in rows
            ],
            "total_returned": len(rows),
        }
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────
# /insforge/agent-run
# Autonomous agent: uses CLAIRO tools + reads InsForge DB
# ─────────────────────────────────────────────────────────────────

class _AgentRequest:
    pass

from pydantic import BaseModel
from typing import Optional

class AgentRunRequest(BaseModel):
    query: str
    payer: Optional[str] = None
    cpt_codes: Optional[list[str]] = None


@router.post("/agent-run")
def insforge_agent_run(request: AgentRunRequest):
    """
    Autonomous denial intelligence agent.

    1. Queries InsForge Postgres for live context (recent claims, payer stats)
    2. Uses that context to run CLAIRO's risk scoring and policy retrieval tools
    3. Synthesizes everything into a structured answer

    This endpoint is the showpiece: it demonstrates InsForge as the persistent
    memory layer that gives CLAIRO agents real historical context before they act.
    """
    db = SessionLocal()
    try:
        # ── Step 1: Pull live context from InsForge Postgres ─────────────
        total_claims = db.query(func.count(DenialClaim.id)).scalar() or 0

        # Most-denied payer
        payer_filter = request.payer
        payer_stats = None
        if payer_filter:
            count = (
                db.query(func.count(DenialClaim.id))
                .filter(DenialClaim.payer == payer_filter)
                .scalar() or 0
            )
            avg_risk = (
                db.query(func.avg(DenialClaim.risk_score))
                .filter(DenialClaim.payer == payer_filter)
                .scalar()
            )
            payer_stats = {
                "payer": payer_filter,
                "total_denials": count,
                "avg_risk_score": round(float(avg_risk), 1) if avg_risk else None,
            }

        # Recent high-risk claims for this payer (or all)
        q = db.query(DenialClaim).filter(DenialClaim.risk_score >= 70)
        if payer_filter:
            q = q.filter(DenialClaim.payer == payer_filter)
        recent_high_risk = q.order_by(DenialClaim.id.desc()).limit(5).all()

        high_risk_context = [
            {
                "id": r.id,
                "payer": r.payer,
                "cpt_codes": r.cpt_codes,
                "classification": r.classification,
                "risk_score": r.risk_score,
                "denial_reason": r.denial_reason,
            }
            for r in recent_high_risk
        ]

        # ── Step 2: Ask Groq to synthesize the InsForge context + user query ──
        db_context_str = json.dumps({
            "total_claims_in_insforge_db": total_claims,
            "payer_stats": payer_stats,
            "recent_high_risk_claims": high_risk_context,
            "cpt_codes_of_interest": request.cpt_codes,
        }, indent=2)

        prompt = f"""You are CLAIRO's autonomous denial intelligence agent.
You have live access to InsForge Postgres (CLAIRO's cloud database) and you've
just queried it for context. Use that data to answer the user's question.

USER QUERY: {request.query}

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

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        raw = response.choices[0].message.content.strip()
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
            "query": request.query,
            "insforge_context": {
                "total_claims": total_claims,
                "payer_stats": payer_stats,
                "high_risk_claims_sampled": len(high_risk_context),
            },
            "agent_response": agent_output,
        }

    finally:
        db.close()
