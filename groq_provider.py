"""Groq LLM provider implementation."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from groq import Groq

from llm_providers import LLMProvider


class GroqProvider(LLMProvider):
    """Groq API provider implementation."""

    def __init__(self, api_key: str):
        """Initialize Groq provider."""
        super().__init__(api_key)
        self.client = Groq(api_key=api_key)
        self._last_raw_response: Optional[str] = None

    def call_completion(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
        reasoning_effort: Optional[str] = None,
        response_format: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make a chat completion call using Groq API."""
        messages = [{"role": "user", "content": prompt}]

        # Groq uses max_completion_tokens instead of max_tokens
        completion = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_completion_tokens=max_tokens,
            response_format=response_format
        )

        content = completion.choices[0].message.content
        self._last_raw_response = content

        # Handle JSON response
        if response_format and response_format.get("type") == "json_object":
            import json
            try:
                return json.loads(content)
            except json.JSONDecodeError as e:
                raise ValueError(f"Failed to parse JSON response: {e}\nContent: {content}")

        return {"content": content}

    def get_provider_name(self) -> str:
        """Return provider name."""
        return "groq"

    def get_api_key_env_var(self) -> str:
        """Return the environment variable name for Groq API key."""
        return "GROQ_API_KEY"

    @classmethod
    def get_api_key_from_env(cls) -> str:
        """Get API key from environment variable."""
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable is required")
        return api_key

    def test_connection(self) -> bool:
        """Test basic connectivity to Groq API."""
        try:
            response = self.call_completion(
                prompt="Return a simple JSON object: {\"test\": \"success\"}",
                model="openai/gpt-oss-120b",  # Use a known working model
                temperature=0.0,
                max_tokens=100,
                response_format={"type": "json_object"}
            )
            return "test" in response and response["test"] == "success"
        except Exception:
            return False

    @property
    def last_raw_response(self) -> Optional[str]:
        """Return the raw response from the most recent API call."""
        return self._last_raw_response