"""Grok (xAI) text + vision helpers for invoice extraction."""

from __future__ import annotations

import base64
import json
import mimetypes
import re
from pathlib import Path
from typing import Any

import httpx


def grok_available(cfg: dict) -> bool:
    return bool((cfg.get("xai") or {}).get("api_key"))


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // 4)


def cost_usd(cfg: dict, tokens_in: int, tokens_out: int) -> float:
    cost = cfg.get("cost") or {}
    inp = float(cost.get("input_per_1m_usd", 5.0))
    out = float(cost.get("output_per_1m_usd", 15.0))
    return (tokens_in / 1_000_000.0) * inp + (tokens_out / 1_000_000.0) * out


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
    temp = temperature if temperature is not None else float(xai.get("temperature", 0.1))

    payload = {
        "model": model,
        "temperature": temp,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    with httpx.Client(timeout=120.0) as client:
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


def vision_chat(
    cfg: dict,
    system: str,
    user_text: str,
    image_path: str | Path | None = None,
    image_b64: str | None = None,
    mime: str = "image/png",
) -> tuple[str, int, int]:
    """
    Call vision-capable Grok with an image (file path or base64).
    Falls back to text-only chat if no image provided.
    """
    xai = cfg.get("xai") or {}
    key = xai.get("api_key")
    if not key:
        raise RuntimeError("XAI_API_KEY not set")

    if not image_b64 and image_path:
        path = Path(image_path)
        raw = path.read_bytes()
        image_b64 = base64.b64encode(raw).decode("ascii")
        guess, _ = mimetypes.guess_type(str(path))
        if guess:
            mime = guess

    if not image_b64:
        return chat(cfg, system, user_text)

    model = xai.get("vision_model") or xai.get("model") or "grok-2-vision-1212"
    base = (xai.get("base_url") or "https://api.x.ai/v1").rstrip("/")
    temp = float(xai.get("temperature", 0.1))

    content: list[dict[str, Any]] = [
        {"type": "text", "text": user_text},
        {
            "type": "image_url",
            "image_url": {"url": f"data:{mime};base64,{image_b64}"},
        },
    ]
    payload = {
        "model": model,
        "temperature": temp,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": content},
        ],
    }
    with httpx.Client(timeout=180.0) as client:
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

    text = data["choices"][0]["message"]["content"]
    usage = data.get("usage") or {}
    tin = int(usage.get("prompt_tokens") or estimate_tokens(system + user_text) + 800)
    tout = int(usage.get("completion_tokens") or estimate_tokens(text))
    return text, tin, tout


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
