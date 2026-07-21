"""Optional Grok helpers."""

from __future__ import annotations

import json
import os
import re
from typing import Any

import httpx


def grok_available(cfg: dict) -> bool:
    return bool((cfg.get("xai") or {}).get("api_key") or os.getenv("XAI_API_KEY"))


def chat(cfg: dict, system: str, user: str, temperature: float = 0.3) -> str:
    key = (cfg.get("xai") or {}).get("api_key") or os.getenv("XAI_API_KEY")
    if not key:
        raise RuntimeError("XAI_API_KEY not set")
    xai = cfg.get("xai") or {}
    model = xai.get("model") or "grok-4-1-fast-reasoning"
    base = (xai.get("base_url") or "https://api.x.ai/v1").rstrip("/")
    with httpx.Client(timeout=90.0) as client:
        resp = client.post(
            f"{base}/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "temperature": temperature,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


def extract_json(text: str) -> Any:
    text = text.strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        text = m.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m2 = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
        if m2:
            return json.loads(m2.group(1))
        raise
