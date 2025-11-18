"""LlamaCpp model provider implementation."""
from strands.models.llamacpp import LlamaCppModel
from .base import BaseModelProvider
from ...config import Config


class LlamaCppProvider(BaseModelProvider):
    """Provider for LlamaCpp models."""

    def __init__(self):
        """Initialize LlamaCpp provider."""
        self.base_url = Config.LLAMA_CPP_URL
        self.max_tokens = Config.LLM_MAX_TOKENS
        self.temperature = Config.LLM_TEMPERATURE

    def get_model(self) -> LlamaCppModel:
        """
        Get LlamaCpp model instance.

        Returns:
            Initialized LlamaCppModel
        """
        return LlamaCppModel(
            base_url=self.base_url,
            model_id="default",
            params={
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "repeat_penalty": 1.1,
            }
        )

    def get_provider_name(self) -> str:
        """Get provider name."""
        return "llamacpp"

    def is_available(self) -> bool:
        """
        Check if LlamaCpp is available.

        Returns:
            True if LLAMA_CPP_URL is configured
        """
        return bool(self.base_url)
