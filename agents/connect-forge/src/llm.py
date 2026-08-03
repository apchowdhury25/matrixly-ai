"""Modular LLM layer (Grok / xAI) with safe offline fallbacks."""

from __future__ import annotations

import re
from typing import Any

import httpx

from .config import prompt_text


def grok_available(cfg: dict) -> bool:
    return bool((cfg.get("xai") or {}).get("api_key"))


def _looks_spanish(text: str) -> bool:
    t = (text or "").lower()
    cues = (
        "hola",
        "gracias",
        "cita",
        "precio",
        "cuánto",
        "cuanto",
        "necesito",
        "ayuda",
        "mañana",
        "manana",
        "por favor",
        "sí",
        "si ",
    )
    return any(c in t for c in cues)


def rule_reply(
    inbound: str,
    *,
    business_name: str = "our team",
    language: str = "auto",
) -> str:
    """Deterministic SMS templates when XAI_API_KEY is missing."""
    text = (inbound or "").strip()
    use_es = language == "es" or (language == "auto" and _looks_spanish(text))
    lower = text.lower()

    if use_es:
        if any(w in lower for w in ("cita", "horario", "mañana", "manana", "appointment")):
            return (
                f"Gracias por escribir a {business_name}. "
                "Podemos confirmar su cita por mensaje. "
                "Responda con el día y hora preferidos, o llámenos."
            )
        if any(w in lower for w in ("precio", "costo", "cuánto", "cuanto")):
            return (
                f"Gracias por contactar a {business_name}. "
                "Con gusto le damos un estimado — "
                "responda con el servicio que necesita y su código postal."
            )
        return (
            f"Hola, gracias por contactar a {business_name}. "
            "Recibimos su mensaje y le ayudamos en breve. "
            "¿En qué podemos asistirle?"
        )

    if any(w in lower for w in ("appoint", "schedule", "book", "confirm", "remind")):
        return (
            f"Thanks for reaching {business_name}. "
            "We can confirm your appointment by text. "
            "Reply with your preferred day/time, or call us."
        )
    if any(w in lower for w in ("price", "cost", "quote", "how much")):
        return (
            f"Thanks for contacting {business_name}. "
            "We can share an estimate — reply with the service you need "
            "and your ZIP (Houston area welcome)."
        )
    if any(w in lower for w in ("missed", "called", "call back", "callback")):
        return (
            f"Sorry we missed your call — this is {business_name}. "
            "How can we help? Reply here or leave the best time to call you back."
        )
    return (
        f"Hi — thanks for contacting {business_name}. "
        "We got your message and will help shortly. "
        "What can we do for you today?"
    )


def generate_reply(
    cfg: dict,
    inbound: str,
    *,
    history: list[dict[str, str]] | None = None,
    language: str = "auto",
) -> tuple[str, dict[str, Any]]:
    """
    Generate an SMS reply.
    Returns (reply_text, meta) where meta includes source: grok|rules.
    """
    business = (cfg.get("business") or {}).get("name") or "our team"
    system = prompt_text("system") or "You write short SMS for a Houston SMB."
    hist = history or []
    hist_txt = "\n".join(
        f"{m.get('role', 'user')}: {m.get('content', '')}" for m in hist[-8:]
    )
    user = (
        f"Business: {business}\n"
        f"Market: Houston SMB (HVAC, home services, contractors, real estate, retail)\n"
        f"Language preference: {language}\n"
        f"Recent thread:\n{hist_txt or '(none)'}\n\n"
        f"Latest inbound SMS:\n{inbound}\n\n"
        "Write only the SMS body to send. No quotes or labels."
    )

    if not grok_available(cfg):
        return rule_reply(inbound, business_name=business, language=language), {
            "source": "rules",
            "reason": "XAI_API_KEY not set",
        }

    xai = cfg.get("xai") or {}
    try:
        payload = {
            "model": xai.get("model") or "grok-4-1-fast-reasoning",
            "temperature": float(xai.get("temperature", 0.4)),
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        base = (xai.get("base_url") or "https://api.x.ai/v1").rstrip("/")
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(
                f"{base}/chat/completions",
                headers={
                    "Authorization": f"Bearer {xai.get('api_key')}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
        content = data["choices"][0]["message"]["content"].strip()
        content = re.sub(r'^["\']|["\']$', "", content)
        if len(content) > 480:
            content = content[:477] + "..."
        return content, {"source": "grok", "model": payload["model"]}
    except Exception as exc:  # noqa: BLE001
        reply = rule_reply(inbound, business_name=business, language=language)
        return reply, {"source": "rules", "reason": f"llm_error: {exc}"}
