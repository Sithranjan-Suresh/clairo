from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from app.rag.retriever import retrieve_policy
from app.services.groq_services import client
import json, re

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
        return {"error": "JSON parsing failed", "raw": text}


@router.post("/prior-auth-check")
def prior_auth_check(request: PriorAuthRequest):
    cpt = request.cpt_codes[0] if request.cpt_codes else ""

    retrieved = retrieve_policy(
        payer=request.payer,
        query="",
        top_k=4,
        classification="prior_authorization",
        cpt=cpt,
        denial_reason="prior authorization requirements precertification criteria"
    )

    policy_text = "\n\n".join([
        f"SOURCE: {p['source']}\nSECTION: Chunk {p['chunk_index']}\n\nCONTENT:\n{p['text']}"
        for p in retrieved
    ])

    policy_source = retrieved[0]["source"] if retrieved else "No policy found"

    prompt = f"""
You are a prior authorization specialist. Compare the submitted clinical notes against the retrieved payer policy and determine what documentation is present, what is missing, and what must be fixed before submitting a prior authorization request.

ANTI-HALLUCINATION RULES:
- Only reference facts explicitly stated in the CLINICAL NOTES below
- Only reference criteria explicitly stated in the RETRIEVED POLICY EVIDENCE
- Do not invent clinical details, diagnoses, or treatments not present in the notes

RETURN ONLY VALID JSON. No preamble, no markdown outside the JSON.

FORMAT:
{{
  "policy_requirements": ["<requirement 1>", "<requirement 2>"],
  "documentation_present": ["<what is present in the clinical notes>"],
  "documentation_missing": ["<what is required by policy but absent from notes>"],
  "recommendation": "<one clear action sentence telling the provider what to fix or submit>",
  "policy_source": "<name of the most relevant policy document cited>"
}}

PAYER: {request.payer}
CPT CODES: {", ".join(request.cpt_codes)}
DIAGNOSIS CODES: {", ".join(request.diagnosis_codes)}

CLINICAL NOTES:
{request.clinical_notes}

RETRIEVED POLICY EVIDENCE:
{policy_text}
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )

    content = response.choices[0].message.content
    result = safe_json_parse(content)

    return {
        "payer": request.payer,
        "cpt_code": cpt,
        **result,
        "policy_source": result.get("policy_source", policy_source)
    }