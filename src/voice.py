"""Text-to-speech module using OpenAI's TTS API."""
import io
import os
from typing import Optional
from openai import OpenAI
from src.logging_config import get_logger

logger = get_logger("chatbot.voice")


class VoiceGenerator:
    """Generate speech from text using OpenAI's TTS API."""

    def __init__(self):
        """Initialize the voice generator with OpenAI client."""
        api_key = os.getenv("OPENAI_API_KEY")
        logger.info(f"[VOICE] Initializing with API key: {'SET' if api_key else 'NOT SET'}")

        self.client = OpenAI(api_key=api_key)
        self.model = "tts-1"  # or "tts-1-hd" for higher quality
        self.voice = "nova"  # Available: alloy, echo, fable, onyx, nova, shimmer
        self.speed = 1.0

        logger.info(f"[VOICE] Initialized: model={self.model}, voice={self.voice}, speed={self.speed}")

    def generate_speech(
        self,
        text: str,
        response_format: str = "wav"
    ) -> Optional[bytes]:
        """
        Generate speech from text.

        Args:
            text: The text to convert to speech
            response_format: Audio format (wav, mp3, opus, aac, flac, pcm)

        Returns:
            Audio data as bytes, or None if generation fails
        """
        try:
            logger.info("=" * 60)
            logger.info(f"[VOICE] Generating speech for text: {text[:100]}...")
            logger.info(f"[VOICE] Using model: {self.model}, voice: {self.voice}, format: {response_format}")

            response = self.client.audio.speech.create(
                model=self.model,
                voice=self.voice,
                input=text,
                response_format=response_format,
                speed=self.speed
            )
            logger.info('[VOICE] Received response from OpenAI TTS API')
            print('[VOICE] Received Audio response from OpenAI TTS API')

            # Read the streaming response into bytes
            audio_data = io.BytesIO()
            chunk_count = 0
            total_bytes = 0

            for chunk in response.iter_bytes():
                chunk_count += 1
                chunk_size = len(chunk)
                total_bytes += chunk_size
                audio_data.write(chunk)

            logger.info(f"[VOICE] Read {chunk_count} chunks, total {total_bytes} bytes")

            audio_bytes = audio_data.getvalue()
            logger.info(f"[VOICE] Successfully generated {len(audio_bytes)} bytes of audio data")

            return audio_bytes

        except Exception as e:
            logger.error(f"[VOICE] ERROR generating speech: {type(e).__name__}: {str(e)}")
            logger.exception("[VOICE] Full traceback:")
            print(f'[VOICE] ERROR: {e}')
            return None


# Singleton instance
_voice_generator = None


def get_voice_generator() -> VoiceGenerator:
    """Get or create the voice generator instance."""
    global _voice_generator
    if _voice_generator is None:
        _voice_generator = VoiceGenerator()
    return _voice_generator
