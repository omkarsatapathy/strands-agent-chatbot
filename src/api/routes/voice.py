"""Voice generation endpoint."""
import hashlib
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response, FileResponse
from pydantic import BaseModel
from src.voice import get_voice_generator
from src.logging_config import get_logger

logger = get_logger("chatbot.routes.voice")

router = APIRouter(prefix="/api", tags=["voice"])

# Audio files storage directory
AUDIO_STORAGE_DIR = Path("frontend/database/audio")
AUDIO_STORAGE_DIR.mkdir(parents=True, exist_ok=True)


class VoiceRequest(BaseModel):
    """Request model for voice generation."""
    text: str
    message_id: int = None  # Optional: for linking to database message
    response_format: str = "wav"


@router.post("/voice/generate")
async def generate_voice(request: VoiceRequest):
    """
    Generate speech from text using OpenAI's TTS API.
    Saves audio to disk and returns the file. If audio already exists, returns cached version.

    Args:
        request: VoiceRequest containing text and optional response_format

    Returns:
        Audio file as binary response
    """
    logger.info("=" * 80)
    logger.info(f"[VOICE] Request received!")
    logger.info(f"[VOICE] Text: {request.text[:100]}...")
    logger.info(f"[VOICE] Format: {request.response_format}")
    logger.info(f"[VOICE] Message ID: {request.message_id}")

    try:
        # Generate unique filename based on text hash
        text_hash = hashlib.md5(request.text.encode()).hexdigest()
        audio_filename = f"audio_{text_hash}.{request.response_format}"
        audio_filepath = AUDIO_STORAGE_DIR / audio_filename

        logger.info(f"[VOICE] Audio file path: {audio_filepath}")

        # Check if audio file already exists
        if audio_filepath.exists():
            logger.info(f"[VOICE] Audio file already exists! Using cached version: {audio_filepath}")
            logger.info(f"[VOICE] Saved OpenAI API call! File size: {audio_filepath.stat().st_size} bytes")

            # Determine content type
            content_types = {
                "wav": "audio/wav",
                "mp3": "audio/mpeg",
                "opus": "audio/opus",
                "aac": "audio/aac",
                "flac": "audio/flac",
                "pcm": "audio/pcm"
            }
            content_type = content_types.get(request.response_format, "audio/wav")

            # Return cached audio file
            return FileResponse(
                path=str(audio_filepath),
                media_type=content_type,
                filename=audio_filename
            )

        # Generate new audio
        logger.info(f"[VOICE] Audio not cached, generating new audio via OpenAI API...")
        voice_generator = get_voice_generator()

        audio_data = voice_generator.generate_speech(
            text=request.text,
            response_format=request.response_format
        )

        if audio_data is None:
            logger.error("[VOICE] Audio data is None - generation failed!")
            raise HTTPException(status_code=500, detail="Failed to generate audio")

        logger.info(f"[VOICE] Successfully generated audio: {len(audio_data)} bytes")

        # Save audio to disk
        with open(audio_filepath, 'wb') as f:
            f.write(audio_data)
        logger.info(f"[VOICE] Audio saved to disk: {audio_filepath}")

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

        # Return the generated audio
        return FileResponse(
            path=str(audio_filepath),
            media_type=content_type,
            filename=audio_filename
        )

    except Exception as e:
        logger.error(f"[VOICE] Exception occurred: {type(e).__name__}: {str(e)}")
        logger.exception("[VOICE] Full traceback:")
        raise HTTPException(status_code=500, detail=f"Error generating audio: {str(e)}")
