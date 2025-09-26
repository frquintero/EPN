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
    
    def call_completion(
        self,
        prompt: str,
        model: str = "llama-3.3-70b-versatile",
        temperature: float = 0.1,
        max_tokens: int = 4096,
        reasoning_effort: str = "low",
        response_format: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Call Groq chat completion."""
        
        if response_format is None:
            response_format = {"type": "json_object"}
        
        try:
            messages = [
                {"role": "user", "content": prompt}
            ]
            
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
