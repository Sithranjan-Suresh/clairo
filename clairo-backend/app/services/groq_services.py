import os
from groq import Groq
from dotenv import load_dotenv

# 1. Load the environment variables from your .env file
load_dotenv()

# 2. Explicitly define and initialize the client in the global scope
client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

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

    # Changed model to the active production string
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile", 
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response.choices[0].message.content

