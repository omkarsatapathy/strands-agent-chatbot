"""OpenAI model provider implementation."""
from strands.models.openai import OpenAIModel
from .base import BaseModelProvider
from ...config import Config


class OpenAIProvider(BaseModelProvider):
    """Provider for OpenAI models."""

    def __init__(self, model_id: str = "gpt-5-mini"):
        """
        Initialize OpenAI provider.

        Args:
            model_id: OpenAI model ID to use (default: gpt-5-mini)
        """
        self.api_key = Config.OPENAI_API_KEY
        self.model_id = Config.OPENAI_MODEL_ID
        self.max_tokens = Config.LLM_MAX_TOKENS
        self.temperature = Config.LLM_TEMPERATURE

    def get_model(self) -> OpenAIModel:
        """
        Get OpenAI model instance.

        Returns:
            Initialized OpenAIModel
        """
        return OpenAIModel(
            client_args={"api_key": self.api_key},
            model_id=self.model_id,
            params={
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
            }
        )

    def get_provider_name(self) -> str:
        """Get provider name."""
        return "openai"

    def is_available(self) -> bool:
        """
        Check if OpenAI is available.

        Returns:
            True if OPENAI_API_KEY is configured
        """
        return bool(self.api_key)
