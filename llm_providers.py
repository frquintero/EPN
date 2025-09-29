"""Abstract LLM provider interface for multi-provider support."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class LLMProvider(ABC):
    """Abstract base class for LLM providers (Groq, DeepSeek, etc.)."""

    def __init__(self, api_key: str):
        """Initialize provider with API key."""
        self.api_key = api_key

    @abstractmethod
    def call_completion(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
        reasoning_effort: Optional[str] = None,
        response_format: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make a chat completion call.

        Args:
            prompt: The prompt text to send
            model: Model identifier (provider-specific)
            temperature: Sampling temperature (0.0 to 1.0+)
            max_tokens: Maximum tokens to generate
            reasoning_effort: Optional reasoning effort level
            response_format: Response format specification (e.g., JSON)

        Returns:
            Dict containing the parsed response

        Raises:
            Exception: If the API call fails
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the provider name (e.g., 'groq', 'deepseek')."""
        pass

    @abstractmethod
    def get_api_key_env_var(self) -> str:
        """Return the environment variable name for this provider's API key."""
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """Test basic connectivity to the provider."""
        pass

    @property
    @abstractmethod
    def last_raw_response(self) -> Optional[str]:
        """Return the raw response from the most recent API call."""
        pass


def create_provider(provider_name: str, api_key: Optional[str] = None) -> LLMProvider:
    """Factory function to create the appropriate provider instance.

    Args:
        provider_name: Name of the provider ('groq' or 'deepseek')
        api_key: API key (if None, will use environment variable)

    Returns:
        Configured provider instance

    Raises:
        ValueError: If provider_name is not supported
        ValueError: If api_key is not provided and env var is missing
    """
    if provider_name.lower() == "groq":
        from groq_provider import GroqProvider
        if api_key is None:
            api_key = GroqProvider.get_api_key_from_env()
        return GroqProvider(api_key)
    elif provider_name.lower() == "deepseek":
        from scripts.deepseek_provider import DeepSeekProvider
        if api_key is None:
            api_key = DeepSeekProvider.get_api_key_from_env()
        return DeepSeekProvider(api_key)
    else:
        raise ValueError(f"Unsupported provider: {provider_name}. Supported: groq, deepseek")