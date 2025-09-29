"""LLM client wrapper supporting multiple providers (Groq, DeepSeek, etc.)."""

import os
import json
from typing import Any, Dict, Optional

# Remove hardcoded groq import - now handled by providers
# from groq import Groq

from llm_providers import LLMProvider, create_provider


class LLMError(Exception):
    """Raised when LLM call fails."""
    pass


class LLMClient:
    """Wrapper for LLM API clients supporting multiple providers."""

    def __init__(self, provider: Optional[LLMProvider] = None, provider_name: str = "groq", api_key: Optional[str] = None):
        """Initialize LLM client with specified provider.

        Args:
            provider: Pre-configured provider instance (optional)
            provider_name: Provider name if no provider instance given ('groq' or 'deepseek')
            api_key: API key (optional, will use environment variable)
        """
        if provider is not None:
            self.provider = provider
        else:
            # Create provider using factory function
            self.provider = create_provider(provider_name, api_key)
    
    def call_completion(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        reasoning_effort: str = "low",
        response_format: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Call LLM completion using the configured provider."""
        # Require all parameters (single source of truth in templates)
        if model is None or temperature is None or max_tokens is None:
            raise LLMError("LLM parameters missing: model/temperature/max_tokens must be set via templates")
        if response_format is None:
            raise LLMError("response_format must be set via templates (e.g., json_object)")
        if isinstance(response_format, str) and response_format.lower() == "json_object":
            response_format = {"type": "json_object"}

        try:
            # Delegate to provider
            return self.provider.call_completion(
                prompt=prompt,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                reasoning_effort=reasoning_effort,
                response_format=response_format
            )

        except Exception as e:
            raise LLMError(f"LLM call failed: {str(e)}")

    @property
    def last_raw_response(self) -> Optional[str]:
        """Return raw content from the most recent LLM call."""
        return self.provider.last_raw_response

    def test_connection(self) -> bool:
        """Test API connection using the provider."""
        return self.provider.test_connection()
