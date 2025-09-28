"""LLM client wrapper for Groq API."""

import os
import json
from typing import Any, Dict, Optional
from groq import Groq


class LLMError(Exception):
    """Raised when LLM call fails."""
    pass


class LLMClient:
    """Wrapper for Groq API client."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Groq client."""
        if api_key is None:
            api_key = os.environ.get("GROQ_API_KEY")
        
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable is required")
        
        self.client = Groq(api_key=api_key)
        self._last_raw_response: Optional[str] = None
    
    def call_completion(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        reasoning_effort: str = "low",
        response_format: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Call Groq chat completion."""
        # Require all parameters (single source of truth in templates)
        if model is None or temperature is None or max_tokens is None:
            raise LLMError("LLM parameters missing: model/temperature/max_tokens must be set via templates")
        if response_format is None:
            raise LLMError("response_format must be set via templates (e.g., json_object)")
        if isinstance(response_format, str) and response_format.lower() == "json_object":
            response_format = {"type": "json_object"}
        
        try:
            messages = []
            # Keep messages minimal; prompt carries all guidance
            messages.append({"role": "user", "content": prompt})
            
            completion = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_completion_tokens=max_tokens,
                response_format=response_format
            )
            
            content = completion.choices[0].message.content
            self._last_raw_response = content
            
            # Handle JSON response (fail-fast without auto-correction)
            if response_format.get("type") == "json_object":
                try:
                    parsed = json.loads(content)
                    return parsed
                except json.JSONDecodeError as e:
                    raise LLMError(f"Failed to parse JSON response: {e}\nContent: {content}")
            
            return {"content": content}
            
        except Exception as e:
            raise LLMError(f"LLM call failed: {str(e)}")

    @property
    def last_raw_response(self) -> Optional[str]:
        """Return raw content from the most recent LLM call."""
        return self._last_raw_response
    
    def test_connection(self) -> bool:
        """Test API connection."""
        try:
            response = self.call_completion(
                prompt="Return a simple JSON object: {\"test\": \"success\"}",
                max_tokens=100
            )
            return "test" in response and response["test"] == "success"
        except Exception:
            return False
