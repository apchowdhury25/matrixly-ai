"""Responder Agent — draft professional replies from KB context."""

from __future__ import annotations

from .. import llm
from ..config import prompt_text
from ..models import SupportState


def run_responder(state: SupportState, cfg: dict) -> SupportState:
    business = (cfg.get("business") or {}).get("name") or "our team"
    ctx = "\n\n---\n\n".join(
        f"Source: {h.source}\n{h.chunk}" for h in state.kb_hits[:4]
    ) or "(no knowledge retrieved)"

    if llm.grok_available(cfg):
        try:
            system = prompt_text("responder") or "Write a support reply from context only."
            system += f"\nBusiness name: {business}"
            user = (
                f"Customer message:\n{state.text}\n\n"
                f"Topic: {state.topic.value} | Urgency: {state.urgency.value}\n"
                f"Retrieval confidence: {state.retrieval_confidence:.2f}\n\n"
                f"Knowledge context:\n{ctx}"
            )
            content, tin, tout = llm.chat(cfg, system, user)
            state.usage_tokens_in += tin
            state.usage_tokens_out += tout
            state.answer = content.strip()
            state.confidence = _blend_confidence(state)
            state.add_audit("responder_llm", confidence=state.confidence)
            return state
        except Exception as e:
            state.add_audit("responder_llm_fallback", error=str(e))

    state.answer = _rule_reply(state, business, ctx)
    state.confidence = _blend_confidence(state)
    state.add_audit("responder_rules", confidence=state.confidence)
    return state


def _blend_confidence(state: SupportState) -> float:
    # Combine retrieval + mild penalty if no hits
    base = state.retrieval_confidence
    if not state.kb_hits:
        base = min(base, 0.25)
    if state.escalate_reason:
        base = min(base, 0.3)
    return round(max(0.0, min(1.0, base)), 3)


def _rule_reply(state: SupportState, business: str, ctx: str) -> str:
    if state.retrieval_confidence < 0.45 or not state.kb_hits:
        return (
            f"Thanks for reaching out to {business}. I want to make sure you get an accurate answer, "
            f"so I'm connecting you with a teammate who can help further. "
            f"If you have an order number or account email, please share it so we can move faster."
        )

    # Use top chunk as basis
    top = state.kb_hits[0].chunk.strip()
    # Trim long chunks
    if len(top) > 700:
        top = top[:700].rsplit(" ", 1)[0] + "…"

    opener = {
        "pricing": "Here's our pricing information:",
        "hours": "Here are our support hours:",
        "order": "Regarding orders and tracking:",
        "policy": "Here's the relevant policy information:",
        "troubleshoot": "Try these troubleshooting steps:",
    }.get(state.topic.value, "Here's what I found:")

    return (
        f"Thanks for contacting {business}. {opener}\n\n"
        f"{top}\n\n"
        f"If this doesn't fully answer your question, reply and I'll escalate to a human specialist."
    )
