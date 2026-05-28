import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def transcribe_audio(audio_bytes: bytes, filename: str = "audio.wav") -> str:
    transcription = client.audio.transcriptions.create(
        file=(filename, audio_bytes),
        model="whisper-large-v3",
        language="en"
    )
    return transcription.text


def parse_voice_intent(transcript: str) -> dict:
    prompt = f"""
You are a medical billing assistant. A user has spoken a command.
Extract the intent and any relevant fields from their speech.

Transcript: "{transcript}"

Return ONLY a JSON object with these fields:
{{
  "intent": one of ["score_claim", "generate_appeal", "check_analytics", "unknown"],
  "payer": extracted payer name or null,
  "cpt_codes": list of CPT codes mentioned or [],
  "documentation_notes": any documentation details mentioned or null,
  "raw_transcript": the original transcript
}}

Return ONLY the JSON. No explanation, no markdown.
"""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    import json
    text = response.choices[0].message.content.strip()
    text = text.replace("```json", "").replace("```", "").strip()
    return json.loads(text)