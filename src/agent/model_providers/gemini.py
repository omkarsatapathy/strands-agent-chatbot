"""Gemini model provider implementation."""
from strands.models.gemini import GeminiModel
from .base import BaseModelProvider
from ...config import Config


class GeminiProvider(BaseModelProvider):
    """Provider for Google Gemini models."""

    def __init__(self, model_id: str = None):
        """
        Initialize Gemini provider.

        Args:
            model_id: Gemini model ID to use (default: from GEMINI_MODEL_ID env var)
        """
        self.api_key = Config.GEMINI_API_KEY
        self.model_id = model_id or Config.GEMINI_MODEL_ID
        self.max_tokens = Config.LLM_MAX_TOKENS
        self.temperature = Config.LLM_TEMPERATURE

    def get_model(self) -> GeminiModel:
        """
        Get Gemini model instance.

        Returns:
            Initialized GeminiModel
        """
        return GeminiModel(
            client_args={"api_key": self.api_key},
            model_id=self.model_id,
            params={
                "temperature": self.temperature,
                "max_output_tokens": self.max_tokens,
                "top_p": 0.9,
                "top_k": 40
            }
        )

    def get_provider_name(self) -> str:
        """Get provider name."""
        return "gemini"

    def is_available(self) -> bool:
        """
        Check if Gemini is available.

        Returns:
            True if GEMINI_API_KEY is configured
        """
        return bool(self.api_key)
