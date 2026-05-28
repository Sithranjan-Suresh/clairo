import json
import re

from app.services.groq_services import client


# -----------------------------
# MAIN FUNCTION
# -----------------------------
def extract_claim_data(raw_text: str):
    """
    Takes raw PDF text and extracts structured insurance claim data using Groq LLM.
    Returns a safe JSON dictionary (never crashes API).
    """

    prompt = f"""
You are a strict medical claim extraction engine.

Your job is to extract structured data from insurance denial documents.

RULES:
- Output ONLY valid JSON
- NO explanations
- NO markdown
- NO code blocks
- NO extra text before or after JSON

Return EXACTLY this JSON schema:

{{
  "payer": null,
  "patient_id": null,
  "cpt_codes": [],
  "denial_reason": null,
  "billed_amount": null,
  "denied_amount": null,
  "service_date": null
}}

IMPORTANT RULES:
- If a field is missing, use null
- CPT codes must be an array of strings
- Amounts should be strings (not floats) if uncertain

DOCUMENT TEXT:
{raw_text}
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0
        )

        content = response.choices[0].message.content

        print("\n--- RAW GROQ OUTPUT ---\n", content, "\n")

        return safe_json_parse(content)

    except Exception as e:
        return {
            "payer": None,
            "patient_id": None,
            "cpt_codes": [],
            "denial_reason": None,
            "billed_amount": None,
            "denied_amount": None,
            "service_date": None,
            "error": f"LLM call failed: {str(e)}"
        }


# -----------------------------
# SAFE JSON PARSER
# -----------------------------
def safe_json_parse(text: str):
    """
    Cleans and parses LLM output safely.
    Prevents crashes from malformed JSON.
    """

    if not text:
        return fallback_error("Empty LLM response")

    text = text.strip()

    # Remove markdown formatting if present
    text = re.sub(r"```json", "", text)
    text = re.sub(r"```", "", text)

    # Extract JSON block if model adds extra text
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        text = match.group(0)

    try:
        data = json.loads(text)

        # Normalize missing fields
        return {
            "payer": data.get("payer"),
            "patient_id": data.get("patient_id"),
            "cpt_codes": data.get("cpt_codes", []),
            "denial_reason": data.get("denial_reason"),
            "billed_amount": data.get("billed_amount"),
            "denied_amount": data.get("denied_amount"),
            "service_date": data.get("service_date"),
        }

    except json.JSONDecodeError:
        return fallback_error("Invalid JSON format from LLM")


# -----------------------------
# FALLBACK RESPONSE
# -----------------------------
def fallback_error(reason: str):
    return {
        "payer": None,
        "patient_id": None,
        "cpt_codes": [],
        "denial_reason": None,
        "billed_amount": None,
        "denied_amount": None,
        "service_date": None,
        "error": reason
    }