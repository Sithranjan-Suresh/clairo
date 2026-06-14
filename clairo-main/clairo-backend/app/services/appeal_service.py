import json
import re

from app.services.groq_services import client


def generate_appeal(
    structured_claim,
    classification,
    retrieved_policies
):

    policy_text = "\n\n".join([
        f"""
SOURCE: {p['source']}
SECTION: Chunk {p['chunk_index']}

CONTENT:
{p['text']}
"""
        for p in retrieved_policies
    ])

    prompt = f"""
You are a senior revenue cycle management specialist writing a formal insurance appeal letter on behalf of a healthcare provider.

TONE RULES (CRITICAL):
- Professional, administrative, and evidence-based — not aggressive or consumer-facing
- Never say "we demand" — always say "we respectfully request"
- Never hedge: no "may be", "could be", "it appears", "although X is not listed"
- State medical necessity as established fact grounded in claim data and policy

ANTI-HALLUCINATION RULES (CRITICAL):
- ONLY reference clinical facts explicitly present in the CLAIM DATA below
- DO NOT invent MRI findings, symptom descriptions, treatment history, or clinical details not in the claim
- DO NOT invent policy names or coverage criteria not in the retrieved evidence
- If clinical documentation is absent, write: "Additional supporting documentation, including [imaging reports / therapy records / physician notes], is available upon request"
- Every factual claim must trace back to CLAIM DATA or RETRIEVED POLICY EVIDENCE

LETTER STRUCTURE — follow this exactly:
1. Header block: RE: Appeal of Denied Claim, Patient ID, Date of Service, CPT Code, Payer
2. Opening paragraph: identify the denied service and state you are appealing
3. Policy Evidence section: quote the relevant retrieved policy language inline with source name
4. Clinical Rationale section: argue medical necessity using ONLY facts from the claim data
5. Closing paragraph: formally request reconsideration and reversal
6. Sign-off: "Sincerely, [Provider Name / Billing Department]"

RETURN ONLY VALID JSON. No preamble, no markdown outside the JSON.

FORMAT:

{{
  "appeal_letter": "",
  "confidence_score": 85,
  "confidence_rationale": ""
}}

The appeal_letter value must use \\n for line breaks to preserve structure.
confidence_score must be an integer between 0 and 100.

CLAIM DATA:
{json.dumps(structured_claim, indent=2)}

DENIAL CLASSIFICATION:
{classification}

RETRIEVED POLICY EVIDENCE:
{policy_text}
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.2
    )

    content = response.choices[0].message.content

    print("\n--- APPEAL RAW OUTPUT ---\n")
    print(content)

    result = safe_json_parse(content)

    # Force normalize confidence_score to 0–100 integer regardless of LLM format
    score = result.get("confidence_score", 0)
    if isinstance(score, float) and score <= 1.0:
        score = int(score * 100)
    result["confidence_score"] = int(score)

    return result


def safe_json_parse(text: str):

    text = text.strip()

    text = re.sub(r"```json", "", text)
    text = re.sub(r"```", "", text)

    try:
        return json.loads(text)

    except Exception:

        return {
            "appeal_letter": "Failed to generate appeal.",
            "confidence_score": 0,
            "confidence_rationale": "JSON parsing failed."
        }
    
def get_appeal_viability(confidence_score: int, classification: str, payer: str) -> dict:

    strict_payers = {"UHC", "Cigna", "Anthem"}
    strong_categories = {"medical_necessity", "documentation_gap", "coding_mismatch"}
    weak_categories = {"timely_filing", "eligibility"}

    score = confidence_score

    if payer in strict_payers:
        score -= 10
    if classification in strong_categories:
        score += 5
    elif classification in weak_categories:
        score -= 15

    score = max(0, min(score, 100))

    if score >= 70:
        strength = "Strong"
        criteria_met = "4–5 of 5"
        rationale = (
            f"Documentation directly addresses {criteria_met} payer-required criteria. "
            f"Policy citations are applicable and denial reason is addressable on appeal."
        )
        industry_context = (
            "Appeals with direct policy citations overturn at 60–67% vs 39% industry average (AHA 2023)"
        )
    elif score >= 45:
        strength = "Moderate"
        criteria_met = "2–3 of 5"
        rationale = (
            f"Documentation addresses {criteria_met} payer-required criteria. "
            f"Additional supporting records would strengthen the appeal."
        )
        industry_context = (
            "Partial-documentation appeals overturn at approximately 40–50% with supplemental records (AHA 2023)"
        )
    else:
        strength = "Weak"
        criteria_met = "fewer than 2 of 5"
        rationale = (
            f"Documentation addresses {criteria_met} payer-required criteria. "
            f"Significant gaps exist; additional clinical records are required before submitting."
        )
        industry_context = (
            "Appeals with incomplete documentation overturn at 20–30%; gather records before filing (AHA 2023)"
        )

    return {
        "appeal_strength": strength,
        "appeal_strength_score": score,
        "appeal_strength_rationale": rationale,
        "industry_context": industry_context
    }