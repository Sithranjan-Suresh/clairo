import json
import re
from app.services.groq_services import client


# ─────────────────────────────────────────
# RULE-BASED LAYER
# Known prior auth requirements and bundling flags
# ─────────────────────────────────────────

PRIOR_AUTH_REQUIRED = {
    "29881", "29880", "29879",  # knee arthroscopy
    "27447", "27448",           # knee replacement
    "22612", "22630",           # spinal fusion
    "70553", "70552",           # brain MRI
    "93306", "93307",           # echo
    "43239", "43240",           # upper GI endoscopy
}

BUNDLING_RISK = {
    ("29881", "29880"): "CPT 29881 and 29880 are commonly bundled — only the higher-paying code is typically reimbursed.",
    ("29881", "29879"): "CPT 29881 and 29879 are frequently bundled — separate billing may trigger a denial.",
    ("93306", "93307"): "CPT 93306 and 93307 should not be billed together — bundling risk is high.",
}

PAYER_KNOWN_STRICT = {"UHC", "Cigna", "Anthem"}

DOCUMENTATION_FLAGS = [
    "no documentation",
    "incomplete",
    "missing notes",
    "not documented",
    "not submitted",
]


def run_rule_based_scoring(cpt_codes: list[str], payer: str, documentation_notes: str) -> dict:
    """
    Returns a rule-based risk score (0–60 max) and list of flags.
    LLM layer adds the remaining 0–40.
    """
    score = 0
    flags = []

    # Prior auth check
    for code in cpt_codes:
        if code in PRIOR_AUTH_REQUIRED:
            score += 25
            flags.append(f"CPT {code} typically requires prior authorization — confirm auth was obtained.")
            break

    # Bundling check
    code_set = set(cpt_codes)
    for pair, message in BUNDLING_RISK.items():
        if set(pair).issubset(code_set):
            score += 20
            flags.append(message)

    # Strict payer check
    if payer in PAYER_KNOWN_STRICT:
        score += 10
        flags.append(f"{payer} has above-average denial rates — ensure all criteria are explicitly documented.")

    # Documentation keyword flags
    notes_lower = documentation_notes.lower()
    for keyword in DOCUMENTATION_FLAGS:
        if keyword in notes_lower:
            score += 15
            flags.append("Documentation notes suggest incomplete records — this significantly increases denial risk.")
            break

    return {
        "rule_based_score": min(score, 60),
        "rule_flags": flags
    }


# ─────────────────────────────────────────
# LLM LAYER
# Documentation completeness analysis
# ─────────────────────────────────────────

def run_llm_scoring(cpt_codes: list[str], payer: str, documentation_notes: str) -> dict:
    """
    Asks Groq to analyze documentation completeness.
    Returns a score (0–40) and specific remediation recommendation.
    """

    prompt = f"""
You are a utilization review specialist evaluating whether a claim's documentation is complete enough to survive an insurance audit.

You will be given:
- CPT codes billed
- Payer name
- Documentation notes from the provider

Your job:
1. Analyze whether the documentation is sufficient to justify medical necessity for the billed CPT codes
2. Identify specific missing elements that would cause a denial (e.g., missing physician notes, no imaging results, no failed conservative treatment documentation)
3. Output a documentation risk score from 0 to 40, where:
   - 0–10 = documentation looks complete
   - 11–25 = some gaps that could cause a denial
   - 26–40 = significant documentation gaps, high denial risk
4. Write one specific remediation recommendation

RULES:
- Base your analysis ONLY on what is present or absent in the documentation notes
- Do NOT invent clinical facts
- Be specific — name exactly what documentation is missing
- Return ONLY valid JSON, no markdown, no preamble

FORMAT:
{{
  "llm_score": 0,
  "remediation": ""
}}

CPT CODES: {cpt_codes}
PAYER: {payer}
DOCUMENTATION NOTES: {documentation_notes}
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        content = response.choices[0].message.content
        return safe_parse_llm_score(content)

    except Exception as e:
        return {"llm_score": 20, "remediation": f"LLM scoring unavailable: {str(e)}"}


def safe_parse_llm_score(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"```json", "", text)
    text = re.sub(r"```", "", text)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        text = match.group(0)
    try:
        data = json.loads(text)
        score = data.get("llm_score", 20)
        if isinstance(score, float) and score <= 1.0:
            score = int(score * 40)
        return {
            "llm_score": max(0, min(int(score), 40)),
            "remediation": data.get("remediation", "No recommendation provided.")
        }
    except Exception:
        return {"llm_score": 20, "remediation": "Failed to parse LLM risk output."}


# ─────────────────────────────────────────
# MAIN SCORING FUNCTION
# ─────────────────────────────────────────

def score_claim(cpt_codes: list[str], payer: str, documentation_notes: str) -> dict:
    """
    Combines rule-based + LLM scoring into a final 0–100 risk score.
    """
    rule_result = run_rule_based_scoring(cpt_codes, payer, documentation_notes)
    llm_result = run_llm_scoring(cpt_codes, payer, documentation_notes)

    total_score = rule_result["rule_based_score"] + llm_result["llm_score"]
    total_score = min(total_score, 100)

    if total_score >= 70:
        risk_level = "HIGH"
    elif total_score >= 40:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    return {
        "risk_score": total_score,
        "risk_level": risk_level,
        "rule_flags": rule_result["rule_flags"],
        "remediation": llm_result["remediation"],
        "breakdown": {
            "rule_based_score": rule_result["rule_based_score"],
            "llm_documentation_score": llm_result["llm_score"]
        }
    }