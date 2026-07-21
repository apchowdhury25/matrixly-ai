"""Optional Grok (xAI) helpers for smarter triage and draft replies."""

from __future__ import annotations

import json
import os
import re
from typing import Any

import httpx


def _api_key(cfg: dict) -> str | None:
    return (cfg.get("xai") or {}).get("api_key") or os.getenv("XAI_API_KEY")


def grok_available(cfg: dict) -> bool:
    return bool(_api_key(cfg))


def chat(cfg: dict, system: str, user: str, temperature: float = 0.2) -> str:
    key = _api_key(cfg)
    if not key:
        raise RuntimeError("XAI_API_KEY not set — rule-based mode only")

    xai = cfg.get("xai") or {}
    model = xai.get("model") or "grok-4-1-fast-reasoning"
    base = (xai.get("base_url") or "https://api.x.ai/v1").rstrip("/")

    payload = {
        "model": model,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    with httpx.Client(timeout=90.0) as client:
        resp = client.post(
            f"{base}/chat/completions",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
    return data["choices"][0]["message"]["content"]


def extract_json(text: str) -> Any:
    text = text.strip()
    # fenced block
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        text = m.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # try first {...} or [...]
        m2 = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
        if m2:
            return json.loads(m2.group(1))
        raise
