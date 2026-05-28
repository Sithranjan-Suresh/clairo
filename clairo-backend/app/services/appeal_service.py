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

    # Payers known to have lower overturn rates
    strict_payers = {"UHC", "Cigna", "Anthem"}

    # Classifications with historically higher overturn rates
    strong_categories = {"medical_necessity", "documentation_gap", "coding_mismatch"}
    weak_categories = {"timely_filing", "eligibility"}

    score = confidence_score

    # Adjust for payer strictness
    if payer in strict_payers:
        score -= 10

    # Adjust for denial type
    if classification in strong_categories:
        score += 5
    elif classification in weak_categories:
        score -= 15

    score = max(0, min(score, 100))

    if score >= 70:
        viability = "High"
        recovery_probability = f"{score - 5}–{min(score + 5, 95)}%"
    elif score >= 45:
        viability = "Medium"
        recovery_probability = f"{score - 10}–{score + 5}%"
    else:
        viability = "Low"
        recovery_probability = f"{max(score - 5, 5)}–{score + 10}%"

    return {
        "viability": viability,
        "recovery_probability": recovery_probability,
        "viability_score": score
    }