import json
import logging
import re
from typing import List, Optional, Union

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app.rag.retriever import retrieve_policy
from app.services.groq_services import client
from app.services.prior_auth_document_service import (
    build_documents_context,
    build_policy_context,
    fallback_pa_packet,
    parse_cpt_codes,
    parse_diagnosis_codes,
    process_uploaded_documents,
)

logger = logging.getLogger(__name__)
router = APIRouter()


class PriorAuthRequest(BaseModel):
    payer: str
    cpt_codes: List[str]
    clinical_notes: str
    diagnosis_codes: List[str] = []


def safe_json_parse(text: str):
    text = text.strip()
    text = re.sub(r"```json", "", text)
    text = re.sub(r"```", "", text)
    try:
        return json.loads(text)
    except Exception:
        return None


def clamp_confidence(value) -> int:
    try:
        num = float(value)
        if 0 < num <= 1:
            num *= 100
        return int(min(100, max(0, round(num))))
    except (TypeError, ValueError):
        return 0


def normalize_pa_required(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return "unknown"
    raw = str(value).strip().lower()
    if raw in ("true", "yes", "required"):
        return True
    if raw in ("false", "no", "not required"):
        return False
    return "unknown"


def normalize_documentation_missing(items: List) -> List[dict]:
    """Coerce documentation_missing entries into dicts so the UI never
    silently drops plain-string items returned by the model."""
    normalized_items: List[dict] = []
    for item in items:
        if isinstance(item, dict):
            normalized_items.append(
                {
                    "missing_item": item.get("missing_item") or item.get("item") or "",
                    "why_needed": item.get("why_needed", ""),
                    "recommended_action": item.get("recommended_action", ""),
                }
            )
        elif item:
            normalized_items.append(
                {
                    "missing_item": str(item),
                    "why_needed": "",
                    "recommended_action": "",
                }
            )
    return normalized_items


def normalize_packet_result(result: dict, payer: str, cpt_codes: List[str]) -> dict:
    normalized = fallback_pa_packet(payer, cpt_codes)
    normalized.update(result)
    normalized["pa_required"] = normalize_pa_required(result.get("pa_required"))
    normalized["confidence"] = clamp_confidence(result.get("confidence", 0))

    for key in (
        "policy_requirements",
        "documentation_present",
        "documentation_missing",
        "clinical_evidence_by_document",
        "recommended_next_steps",
    ):
        if not isinstance(normalized.get(key), list):
            normalized[key] = []

    normalized["documentation_missing"] = normalize_documentation_missing(
        normalized["documentation_missing"]
    )

    for req in normalized["policy_requirements"]:
        if isinstance(req, dict):
            status = str(req.get("status", "unclear")).lower()
            if status not in ("met", "missing", "unclear"):
                req["status"] = "unclear"
            if req.get("source_document"):
                req["source_document"] = _clean_source_label(req["source_document"])

    return normalized


def _clean_source_label(source: str) -> str:
    if not source:
        return "Uploaded Document"
    cleaned = source.replace("\\", "/")
    if "app/data/policies/" in cleaned.lower():
        cleaned = cleaned.split("/")[-1]
    cleaned = cleaned.replace("_", " ").replace("-", " ")
    return cleaned.strip().title() or "Uploaded Document"


def _normalize_upload_files(
    files: Optional[Union[List[UploadFile], UploadFile]],
) -> List[UploadFile]:
    if files is None:
        return []
    if isinstance(files, list):
        return files
    return [files]


PA_PACKET_JSON_SCHEMA = """
{
  "pa_required": true,
  "confidence": 85,
  "requested_service_summary": "...",
  "medical_necessity_summary": "...",
  "policy_requirements": [
    {
      "requirement": "...",
      "status": "met",
      "supporting_evidence": "...",
      "source_document": "..."
    }
  ],
  "documentation_present": [
    {
      "document": "...",
      "key_findings": ["...", "..."]
    }
  ],
  "documentation_missing": [
    {
      "missing_item": "...",
      "why_needed": "...",
      "recommended_action": "..."
    }
  ],
  "clinical_evidence_by_document": [
    {
      "document_name": "...",
      "evidence_found": ["...", "..."]
    }
  ],
  "provider_ready_summary": "...",
  "recommended_next_steps": ["...", "..."],
  "doctor_review_notes": "..."
}
"""


async def _build_prior_auth_packet(
    payer: str,
    cpt_list: List[str],
    dx_list: List[str],
    notes: str,
    upload_files: List[UploadFile],
):
    logger.info(
        "Prior auth packet request: payer=%s cpt=%s diagnosis=%s files=%d notes_len=%d",
        payer,
        cpt_list,
        dx_list,
        len(upload_files),
        len(notes),
    )
    for upload in upload_files:
        logger.info("Prior auth file received: %s", upload.filename)

    if not upload_files and not notes:
        raise HTTPException(
            status_code=400,
            detail="Please upload at least one clinical document or enter clinical notes.",
        )

    documents, warnings = await process_uploaded_documents(upload_files)
    documents_context = build_documents_context(documents) if documents else ""

    if not documents and not notes:
        raise HTTPException(
            status_code=400,
            detail="Please upload at least one clinical document or enter clinical notes, "
            "and ensure uploaded files contain readable text.",
        )

    logger.info(
        "Prior auth extraction complete: documents=%d warnings=%d",
        len(documents),
        len(warnings),
    )

    cpt_primary = cpt_list[0]
    try:
        retrieved = retrieve_policy(
            payer=payer,
            query="",
            top_k=4,
            classification="prior_authorization",
            cpt=cpt_primary,
            denial_reason="prior authorization requirements precertification criteria",
        )
    except Exception as exc:
        logger.exception("Prior auth policy retrieval failed")
        warnings.append(f"Policy retrieval failed: {exc}")
        retrieved = []

    policy_text, policy_source = build_policy_context(retrieved)

    prompt = f"""
You are a prior authorization specialist building a provider-ready prior authorization packet for {payer}.

STRICT RULES:
- Only use facts from UPLOADED DOCUMENTS, MANUAL CLINICAL NOTES, or RETRIEVED PAYER POLICY EVIDENCE below.
- Do NOT invent patient history, diagnoses, treatments, dates, outcomes, or policy criteria.
- If information is missing, mark requirements as "missing" or "unclear".
- Use readable document names only (never raw file paths like app/data/policies/...).
- Output valid JSON only. No markdown. No preamble.

STATUS VALUES for policy_requirements:
- "met"
- "missing"
- "unclear"

Return JSON matching this schema:
{PA_PACKET_JSON_SCHEMA}

PAYER: {payer}
CPT CODES: {", ".join(cpt_list)}
DIAGNOSIS CODES: {", ".join(dx_list) if dx_list else "Not provided"}

ADDITIONAL CLINICAL CONTEXT:
{notes or "None provided"}

UPLOADED DOCUMENTS:
{documents_context or "No documents uploaded"}

RETRIEVED PAYER POLICY EVIDENCE:
{policy_text or "No payer policy evidence retrieved"}
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        content = response.choices[0].message.content or ""
        logger.info("Prior auth Groq response received (%d chars)", len(content))
    except Exception as exc:
        logger.exception("Prior auth Groq call failed")
        packet = fallback_pa_packet(
            payer,
            cpt_list,
            warnings=warnings,
            groq_error=str(exc),
        )
        return {
            "payer": payer,
            "cpt_codes": cpt_list,
            "diagnosis_codes": dx_list,
            "documents_processed": [
                {
                    "filename": doc["filename"],
                    "display_name": doc["display_name"],
                    "document_type": doc["document_type"],
                    "text_preview": doc["text_preview"],
                }
                for doc in documents
            ],
            "warnings": warnings,
            "policy_source": policy_source,
            "packet": packet,
        }

    parsed = safe_json_parse(content)
    if parsed is None:
        logger.warning("Prior auth Groq JSON parse failed")
        packet = fallback_pa_packet(
            payer,
            cpt_list,
            warnings=warnings,
            raw=content,
        )
    else:
        packet = normalize_packet_result(parsed, payer, cpt_list)

    return {
        "payer": payer,
        "cpt_codes": cpt_list,
        "diagnosis_codes": dx_list,
        "documents_processed": [
            {
                "filename": doc["filename"],
                "display_name": doc["display_name"],
                "document_type": doc["document_type"],
                "text_preview": doc["text_preview"],
            }
            for doc in documents
        ],
        "warnings": warnings,
        "policy_source": policy_source,
        "packet": packet,
    }


@router.post("/prior-auth-check")
async def prior_auth_check(request: PriorAuthRequest):
    if not request.payer.strip():
        raise HTTPException(status_code=400, detail="Payer is required.")
    if not request.cpt_codes:
        raise HTTPException(status_code=400, detail="At least one CPT code is required.")
    if not request.clinical_notes.strip():
        raise HTTPException(status_code=400, detail="Clinical notes are required.")

    cpt = request.cpt_codes[0]

    try:
        retrieved = retrieve_policy(
            payer=request.payer,
            query="",
            top_k=4,
            classification="prior_authorization",
            cpt=cpt,
            denial_reason="prior authorization requirements precertification criteria",
        )
    except Exception as exc:
        logger.exception("Prior auth policy retrieval failed")
        raise HTTPException(
            status_code=500,
            detail=f"Policy retrieval failed: {exc}",
        ) from exc

    policy_text = "\n\n".join(
        [
            f"SOURCE: {_clean_source_label(p['source'])}\nSECTION: Chunk {p['chunk_index']}\n\nCONTENT:\n{p['text']}"
            for p in retrieved
        ]
    )

    policy_source = (
        _clean_source_label(retrieved[0]["source"]) if retrieved else "No policy found"
    )

    prompt = f"""
You are a prior authorization specialist reviewing a real clinical case for submission to {request.payer}.

STRICT RULES:
- Only cite criteria EXPLICITLY stated in the RETRIEVED POLICY EVIDENCE below
- Only cite clinical facts EXPLICITLY stated in the CLINICAL NOTES below
- Never invent, infer, or extrapolate any clinical detail or policy requirement
- If a specific policy criterion cannot be found in the evidence, write: "Policy not retrieved — verify manually"

TASK:
1. Identify whether prior authorization is required for CPT {", ".join(request.cpt_codes)} under this payer's policy
2. List each specific PA criterion from the policy as its own requirement object
3. For each criterion, check whether the clinical notes satisfy it — quote the supporting text if present
4. Flag any criterion the notes do NOT address as missing
5. Assign urgency based on how many criteria are unmet: high (2+), medium (1), low (0)

RETURN ONLY VALID JSON. No markdown, no preamble, no trailing text.

FORMAT:
{{
  "pa_required": true,
  "policy_requirements": [
    {{
      "requirement": "<exact criterion from policy>",
      "met": true,
      "evidence_in_notes": "<direct quote or brief summary from clinical notes, or null if not met>"
    }}
  ],
  "documentation_present": ["<specific item found in clinical notes>"],
  "documentation_missing": ["<specific criterion required by policy but absent from notes>"],
  "urgency": "high | medium | low",
  "recommendation": "<one concrete action sentence: what the provider must add, fix, or resubmit>",
  "policy_source": "<source document name from the evidence>"
}}

PAYER: {request.payer}
CPT CODES: {", ".join(request.cpt_codes)}
DIAGNOSIS CODES: {", ".join(request.diagnosis_codes)}

CLINICAL NOTES:
{request.clinical_notes}

RETRIEVED POLICY EVIDENCE:
{policy_text}
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        content = response.choices[0].message.content or ""
    except Exception as exc:
        logger.exception("Prior auth Groq call failed")
        raise HTTPException(
            status_code=502,
            detail=f"Prior auth model call failed: {exc}",
        ) from exc

    result = safe_json_parse(content) or {}

    packet = {
        "pa_required": normalize_pa_required(result.get("pa_required", True)),
        "urgency": result.get("urgency", "medium"),
        "policy_requirements": result.get("policy_requirements", []),
        "documentation_present": result.get("documentation_present", []),
        "documentation_missing": normalize_documentation_missing(
            result.get("documentation_missing", [])
        ),
        "recommendation": result.get("recommendation", ""),
        "policy_source": result.get("policy_source", policy_source),
    }

    if not isinstance(packet["policy_requirements"], list):
        packet["policy_requirements"] = []
    if not isinstance(packet["documentation_present"], list):
        packet["documentation_present"] = []

    return {
        "payer": request.payer,
        "cpt_code": cpt,
        "cpt_codes": request.cpt_codes,
        "diagnosis_codes": request.diagnosis_codes,
        "policy_source": policy_source,
        "packet": packet,
    }


@router.post("/prior-auth-check-documents")
async def prior_auth_check_documents(
    payer: str = Form(...),
    cpt_codes: str = Form(...),
    diagnosis_codes: str = Form(""),
    clinical_notes: str = Form(""),
    files: List[UploadFile] = File(default=[]),
):
    notes = (clinical_notes or "").strip()
    cpt_list = parse_cpt_codes(cpt_codes)
    dx_list = parse_diagnosis_codes(diagnosis_codes)
    upload_files = _normalize_upload_files(files)

    if not upload_files and not notes:
        raise HTTPException(
            status_code=400,
            detail="Please upload at least one clinical document or enter clinical notes.",
        )

    if not payer.strip():
        raise HTTPException(status_code=400, detail="Payer is required.")
    if not cpt_list:
        raise HTTPException(status_code=400, detail="At least one CPT code is required.")

    try:
        return await _build_prior_auth_packet(
            payer.strip(),
            cpt_list,
            dx_list,
            notes,
            upload_files,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Prior auth packet generation failed")
        raise HTTPException(
            status_code=500,
            detail=f"Prior authorization packet generation failed: {exc}",
        ) from exc
