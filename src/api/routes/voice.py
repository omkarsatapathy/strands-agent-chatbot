"""Voice generation endpoint."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from src.voice import get_voice_generator
from src.logging_config import get_logger

logger = get_logger("chatbot.routes.voice")

router = APIRouter(prefix="/api", tags=["voice"])


class VoiceRequest(BaseModel):
    """Request model for voice generation."""
    text: str
    response_format: str = "wav"


@router.post("/voice/generate")
async def generate_voice(request: VoiceRequest):
    """
    Generate speech from text using OpenAI's TTS API.

    Args:
        request: VoiceRequest containing text and optional response_format

    Returns:
        Audio file as binary response
    """
    logger.info("=" * 80)
    logger.info(f"[VOICE] Request received!")
    logger.info(f"[VOICE] Text: {request.text[:100]}...")
    logger.info(f"[VOICE] Format: {request.response_format}")

    try:
        voice_generator = get_voice_generator()
        logger.info(f"[VOICE] Voice generator obtained: {voice_generator}")

        audio_data = voice_generator.generate_speech(
            text=request.text,
            response_format=request.response_format
        )

        if audio_data is None:
            logger.error("[VOICE] Audio data is None - generation failed!")
            raise HTTPException(status_code=500, detail="Failed to generate audio")

        logger.info(f"[VOICE] Successfully generated audio: {len(audio_data)} bytes")

        # Determine content type based on format
        content_types = {
            "wav": "audio/wav",
            "mp3": "audio/mpeg",
            "opus": "audio/opus",
            "aac": "audio/aac",
            "flac": "audio/flac",
            "pcm": "audio/pcm"
        }

        content_type = content_types.get(request.response_format, "audio/wav")
        logger.info(f"[VOICE] Returning response with content-type: {content_type}")

        return Response(
            content=audio_data,
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename=speech.{request.response_format}"
            }
        )
    except Exception as e:
        logger.error(f"[VOICE] Exception occurred: {type(e).__name__}: {str(e)}")
        logger.exception("[VOICE] Full traceback:")
        raise HTTPException(status_code=500, detail=f"Error generating audio: {str(e)}")
