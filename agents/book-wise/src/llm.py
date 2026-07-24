"""Grok (xAI) helpers."""

from __future__ import annotations

import json
import re
from typing import Any

import httpx


def grok_available(cfg: dict) -> bool:
    return bool((cfg.get("xai") or {}).get("api_key"))


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // 4)


def chat(
    cfg: dict,
    system: str,
    user: str,
    temperature: float | None = None,
) -> tuple[str, int, int]:
    xai = cfg.get("xai") or {}
    key = xai.get("api_key")
    if not key:
        raise RuntimeError("XAI_API_KEY not set")

    model = xai.get("model") or "grok-4-1-fast-reasoning"
    base = (xai.get("base_url") or "https://api.x.ai/v1").rstrip("/")
    temp = temperature if temperature is not None else float(xai.get("temperature", 0.2))

    payload = {
        "model": model,
        "temperature": temp,
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

    content = data["choices"][0]["message"]["content"]
    usage = data.get("usage") or {}
    tin = int(usage.get("prompt_tokens") or estimate_tokens(system + user))
    tout = int(usage.get("completion_tokens") or estimate_tokens(content))
    return content, tin, tout


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


def cost_usd(cfg: dict, tokens_in: int, tokens_out: int) -> float:
    cost = cfg.get("cost") or {}
    inp = float(cost.get("input_per_1m_usd", 5.0))
    out = float(cost.get("output_per_1m_usd", 15.0))
    return (tokens_in / 1_000_000.0) * inp + (tokens_out / 1_000_000.0) * out
