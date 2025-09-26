"""LLM client wrapper for Groq API."""

import os
import json
from typing import Any, Dict, Optional
from llm_config import get_default_llm_config
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
        # Fall back to centralized defaults if any parameter is missing
        defaults = get_default_llm_config()
        if model is None:
            model = defaults["model"]
        if temperature is None:
            temperature = defaults["temperature"]
        if max_tokens is None:
            max_tokens = defaults["max_tokens"]
        if response_format is None:
            response_format = defaults["response_format"]
        
        try:
            messages = []
            # Add a system hint to satisfy providers that require explicit JSON mention
            if response_format.get("type") == "json_object":
                messages.append({"role": "system", "content": "Return only JSON. Respond with a valid JSON object."})
            messages.append({"role": "user", "content": prompt})
            
            # Add assistant priming for JSON
            if response_format.get("type") == "json_object":
                messages.append({"role": "assistant", "content": "{"})
            
            completion = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_completion_tokens=max_tokens,
                response_format=response_format
            )
            
            content = completion.choices[0].message.content
            
            # Handle JSON response
            if response_format.get("type") == "json_object":
                if not content.strip().startswith('{'):
                    content = "{" + content
                
                try:
                    parsed = json.loads(content)
                    return parsed
                except json.JSONDecodeError as e:
                    raise LLMError(f"Failed to parse JSON response: {e}\nContent: {content}")
            
            return {"content": content}
            
        except Exception as e:
            raise LLMError(f"LLM call failed: {str(e)}")
    
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
