import os
from groq import Groq
from dotenv import load_dotenv

# 1. Load the environment variables from your .env file
load_dotenv()

# 2. Explicitly define and initialize the client in the global scope
client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

# Groq periodically deprecates/retires models (llama-3.3-70b-versatile was
# retired to Enterprise-only access on 2026-08-16, breaking every AI
# feature in this app until this was caught and fixed). Keep the model ID
# in exactly one place so the next migration is a one-line change instead
# of an 8-file grep-and-replace. Override via GROQ_CHAT_MODEL if Groq
# retires this one too, without needing a code change/redeploy.
CHAT_MODEL = os.getenv("GROQ_CHAT_MODEL", "openai/gpt-oss-120b")


def analyze_denial(text: str):
    prompt = f"""
    You are a healthcare denial analyst.

    Analyze this denial letter and provide:
    1. Likely denial reason
    2. Short summary
    3. Recommended next action

    Denial Letter:
    {text}
    """

    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response.choices[0].message.content

