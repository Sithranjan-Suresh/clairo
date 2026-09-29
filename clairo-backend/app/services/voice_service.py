import json
import logging
import os

from groq import Groq
from dotenv import load_dotenv

from app.services.groq_services import CHAT_MODEL

load_dotenv()

logger = logging.getLogger(__name__)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


class VoiceProcessingError(Exception):
    """Raised when transcription or intent parsing fails, so the route can
    return a clean error response instead of a bare 500."""


def transcribe_audio(audio_bytes: bytes, filename: str = "audio.wav") -> str:
    try:
        transcription = client.audio.transcriptions.create(
            file=(filename, audio_bytes),
            model="whisper-large-v3",
            language="en"
        )
        return transcription.text
    except Exception as exc:
        logger.exception("Voice transcription failed")
        raise VoiceProcessingError(f"Transcription failed: {exc}") from exc


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
    try:
        response = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        text = response.choices[0].message.content.strip()
    except Exception as exc:
        logger.exception("Voice intent LLM call failed")
        raise VoiceProcessingError(f"Intent parsing failed: {exc}") from exc

    text = text.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning("Voice intent JSON parse failed: %s", text[:200])
        return {
            "intent": "unknown",
            "payer": None,
            "cpt_codes": [],
            "documentation_notes": None,
            "raw_transcript": transcript,
        }