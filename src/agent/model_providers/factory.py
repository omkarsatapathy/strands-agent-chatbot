"""Factory for creating model provider instances."""
from typing import Optional
from .base import BaseModelProvider
from .llamacpp import LlamaCppProvider
from .gemini import GeminiProvider
from .openai import OpenAIProvider


class ModelProviderFactory:
    """Factory for creating model provider instances."""

    # Registry of available providers
    _providers = {
        "llamacpp": LlamaCppProvider,
        "gemini": GeminiProvider,
        "openai": OpenAIProvider,
    }

    @classmethod
    def create_provider(cls, provider_name: str, **kwargs) -> BaseModelProvider:
        """
        Create a model provider instance.

        Args:
            provider_name: Name of the provider ('llamacpp', 'gemini', 'openai')
            **kwargs: Additional arguments to pass to the provider constructor

        Returns:
            Initialized provider instance

        Raises:
            ValueError: If provider_name is not recognized or provider is not available
        """
        provider_name = provider_name.lower()

        if provider_name not in cls._providers:
            available = ", ".join(cls._providers.keys())
            raise ValueError(
                f"Unknown provider '{provider_name}'. Available providers: {available}"
            )

        # Create provider instance
        provider_class = cls._providers[provider_name]
        provider = provider_class(**kwargs)

        # Check if provider is available
        if not provider.is_available():
            raise ValueError(
                f"Provider '{provider_name}' is not properly configured. "
                f"Please check your configuration settings."
            )

        return provider

    @classmethod
    def get_available_providers(cls) -> list[dict[str, str]]:
        """
        Get list of available and configured providers.

        Returns:
            List of dicts with provider info (name, display_name, available)
        """
        providers = []
        provider_display_names = {
            "llamacpp": "LlamaCpp (Local)",
            "gemini": "Google Gemini",
            "openai": "OpenAI GPT",
        }

        for name, provider_class in cls._providers.items():
            try:
                provider = provider_class()
                is_available = provider.is_available()
            except Exception:
                is_available = False

            providers.append({
                "name": name,
                "display_name": provider_display_names.get(name, name),
                "available": is_available
            })

        return providers

    @classmethod
    def get_default_provider(cls) -> str:
        """
        Get the default provider name.

        Returns the first available provider in priority order:
        1. llamacpp (local)
        2. gemini
        3. openai

        Returns:
            Name of the default provider

        Raises:
            RuntimeError: If no providers are available
        """
        priority_order = ["llamacpp", "gemini", "openai"]

        for provider_name in priority_order:
            try:
                provider_class = cls._providers[provider_name]
                provider = provider_class()
                if provider.is_available():
                    return provider_name
            except Exception:
                continue

        raise RuntimeError(
            "No model providers are configured. Please configure at least one provider."
        )
