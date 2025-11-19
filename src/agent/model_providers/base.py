"""Base class for model providers."""
from abc import ABC, abstractmethod
from typing import Any


class BaseModelProvider(ABC):
    """Abstract base class for model providers."""

    @abstractmethod
    def get_model(self) -> Any:
        """
        Get the initialized model instance.

        Returns:
            The model instance compatible with Strands Agent
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """
        Get the name of the provider.

        Returns:
            Provider name (e.g., 'llamacpp', 'gemini', 'openai')
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the provider is properly configured and available.

        Returns:
            True if the provider can be used, False otherwise
        """
        pass
