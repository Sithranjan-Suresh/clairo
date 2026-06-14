from app.services.groq_services import client


def classify_denial(structured_claim: dict):

    prompt = f"""
You are a medical insurance denial classification engine.

Classify the claim into EXACTLY ONE category.

Allowed categories:
- medical_necessity
- prior_authorization
- coding_mismatch
- eligibility
- documentation_gap
- timely_filing

RULES:
- Output ONLY the category name
- No explanation
- No extra text
- No punctuation

CLAIM:
{structured_claim}
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )

    return response.choices[0].message.content.strip()