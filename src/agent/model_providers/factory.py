"""Factory for creating model provider instances."""
from typing import Optional
from .base import BaseModelProvider
from .llamacpp import LlamaCppProvider, LlamaCppGptOssProvider, LlamaCppQwen3Provider
from .gemini import GeminiProvider
from .openai import OpenAIProvider


class ModelProviderFactory:
    """Factory for creating model provider instances."""

    # Registry of available providers
    _providers = {
        "llamacpp-gpt-oss": LlamaCppGptOssProvider,
        "llamacpp-qwen3": LlamaCppQwen3Provider,
        "llamacpp": LlamaCppProvider,  # Backward compatibility (defaults to Qwen3)
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
            "llamacpp-gpt-oss": "LlamaCPP-GPT-OSS",
            "llamacpp-qwen3": "LlamaCPP-Qwen3-8B",
            "llamacpp": "LlamaCpp (Local)",  # Hidden, backward compat
            "gemini": "Google Gemini",
            "openai": "OpenAI GPT",
        }

        # Skip the backward-compat 'llamacpp' entry in the UI
        skip_providers = {"llamacpp"}

        for name, provider_class in cls._providers.items():
            if name in skip_providers:
                continue

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
        1. llamacpp-qwen3 (local)
        2. llamacpp-gpt-oss (local)
        3. openai
        4. gemini

        Returns:
            Name of the default provider

        Raises:
            RuntimeError: If no providers are available
        """
        priority_order = ["llamacpp-qwen3", "llamacpp-gpt-oss", "openai", "gemini"]

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
