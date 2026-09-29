from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from app.services.voice_service import (
    VoiceProcessingError,
    transcribe_audio,
    parse_voice_intent,
)
from app.services.risk_service import score_claim
from app.services.analytics_service import get_summary_stats

router = APIRouter()

MAX_AUDIO_BYTES = 20 * 1024 * 1024  # 20 MB


@router.post("/process")
async def process_voice(file: UploadFile = File(...)):

    audio_bytes = await file.read()
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="Audio file too large (max 20 MB).")
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="No audio data received.")

    try:
        # Step 1: Transcribe
        transcript = transcribe_audio(audio_bytes, filename=file.filename)

        # Step 2: Parse intent
        intent_data = parse_voice_intent(transcript)
    except VoiceProcessingError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    intent = intent_data.get("intent", "unknown")

    # Step 3: Route to correct endpoint
    if intent == "score_claim":
        cpt_codes = intent_data.get("cpt_codes", [])
        payer = intent_data.get("payer") or "Unknown"
        notes = intent_data.get("documentation_notes") or ""

        if not cpt_codes:
            return JSONResponse({
                "transcript": transcript,
                "intent": intent,
                "error": "No CPT codes detected in your request. Please mention the procedure code."
            })

        result = score_claim(
            cpt_codes=cpt_codes,
            payer=payer,
            documentation_notes=notes
        )

        return {
            "transcript": transcript,
            "intent": intent,
            "payer": payer,
            "cpt_codes": cpt_codes,
            "result": result,
            "voice_response": f"Risk score for {payer} claim with CPT {', '.join(cpt_codes)} is {result['risk_score']} out of 100, rated {result['risk_level']}. {result['remediation']}"
        }

    elif intent == "check_analytics":
        stats = get_summary_stats()
        return {
            "transcript": transcript,
            "intent": intent,
            "result": stats,
            "voice_response": f"Your practice has processed {stats['total_denials_processed']} denials with a denial rate of {stats['practice_denial_rate']}, compared to the industry average of {stats['industry_denial_rate']}."
        }

    else:
        return {
            "transcript": transcript,
            "intent": intent,
            "voice_response": "I understood your request but couldn't route it to a specific action. Try asking to score a claim or check your analytics.",
            "raw": intent_data
        }