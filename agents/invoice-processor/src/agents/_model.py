"""Shared model resolution for Pydantic AI agents."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any, Optional


@lru_cache(maxsize=4)
def resolve_model(preferred: str = "xai:grok-4.5") -> str:
    """
    Return a pydantic-ai model string.

    Prefer native `xai:` provider when XAI_API_KEY is set.
    Allow env override for local testing with other providers.
    """
    env_model = os.getenv("INVOICE_PROCESSOR_MODEL")
    if env_model:
        return env_model
    fallback = os.getenv("INVOICE_PROCESSOR_MODEL_FALLBACK") or "xai:grok-4-1-fast-reasoning"
    # Keep preferred first; callers can catch provider errors and retry fallback
    return preferred or fallback


def try_import_pydantic_ai() -> tuple[Any, Any, Any] | None:
    """Import Agent, RunContext, or return None if package missing."""
    try:
        from pydantic_ai import Agent, RunContext  # type: ignore

        return Agent, RunContext, True
    except ImportError:
        return None


def llm_enabled(deps: Any) -> bool:
    """True when pydantic-ai is installed and credentials exist."""
    if try_import_pydantic_ai() is None:
        return False
    return bool(getattr(deps, "model_available", lambda: False)())
