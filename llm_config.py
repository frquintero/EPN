"""Centralized LLM configuration for the EPN app.

Provides a single source of truth for default LLM parameters, optional
environment overrides, and a merger utility for per-role overrides.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class LLMDefaults:
    model: str = "openai/gpt-oss-120b"
    temperature: float = 0.1
    max_tokens: int = 4096
    # Keep in structure for compatibility; not all models support it and the
    # client does not currently forward it to the API call.
    reasoning_effort: str = "low"
    response_format: Dict[str, Any] = None  # set via factory below


def _default_response_format() -> Dict[str, Any]:
    return {"type": "json_object"}


def get_default_llm_config() -> Dict[str, Any]:
    """Return default config merged with environment overrides.

    Environment overrides (optional):
      - EPN_LLM_MODEL
      - EPN_LLM_TEMPERATURE (float)
      - EPN_LLM_MAX_TOKENS (int)
      - EPN_LLM_REASONING_EFFORT
      - EPN_LLM_RESPONSE_FORMAT ("json_object" currently supported)
    """
    base = asdict(LLMDefaults(response_format=_default_response_format()))

    env_model = os.getenv("EPN_LLM_MODEL")
    if env_model:
        base["model"] = env_model

    env_temp = os.getenv("EPN_LLM_TEMPERATURE")
    if env_temp:
        try:
            base["temperature"] = float(env_temp)
        except ValueError:
            pass

    env_max = os.getenv("EPN_LLM_MAX_TOKENS")
    if env_max:
        try:
            base["max_tokens"] = int(env_max)
        except ValueError:
            pass

    env_re = os.getenv("EPN_LLM_REASONING_EFFORT")
    if env_re:
        base["reasoning_effort"] = env_re

    env_rf = os.getenv("EPN_LLM_RESPONSE_FORMAT")
    if env_rf:
        # Support simple selector for now
        if env_rf.lower() == "json_object":
            base["response_format"] = _default_response_format()

    # Ensure response_format exists
    if not isinstance(base.get("response_format"), dict):
        base["response_format"] = _default_response_format()

    return base


def merge_llm_config(overrides: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge defaults (with env overrides) and provided per-role overrides.

    Per-role overrides take precedence.
    """
    merged = get_default_llm_config()
    if overrides:
        for k, v in overrides.items():
            # Only accept known keys
            if k in {"model", "temperature", "max_tokens", "reasoning_effort", "response_format"}:
                merged[k] = v
    # Guarantee response_format present
    if not isinstance(merged.get("response_format"), dict):
        merged["response_format"] = _default_response_format()
    return merged

