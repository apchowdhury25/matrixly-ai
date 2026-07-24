"""Triage Agent — urgency, sentiment, topic."""

from __future__ import annotations

import re
from typing import Any

from .. import llm
from ..config import prompt_text
from ..models import Sentiment, SupportState, Topic, Urgency

_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
_PHONE = re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
_CARD = re.compile(r"\b(?:\d[ -]*?){13,19}\b")


def run_triage(state: SupportState, cfg: dict) -> SupportState:
    text = state.text or ""
    lower = text.lower()

    # Keyword force-escalate
    for kw in cfg.get("escalate_keywords") or []:
        if kw.lower() in lower:
            state.escalate_reason = f"keyword:{kw}"
            state.urgency = Urgency.critical
            break

    pii: list[str] = []
    if _EMAIL.search(text):
        pii.append("email")
    if _PHONE.search(text):
        pii.append("phone")
    if _CARD.search(text):
        pii.append("card")
    state.pii_flags = pii

    if llm.grok_available(cfg):
        try:
            system = prompt_text("triage") or "Classify support message as JSON."
            user = f"Message:\n{text}"
            if state.subject:
                user = f"Subject: {state.subject}\n\n{user}"
            content, tin, tout = llm.chat(cfg, system, user)
            state.usage_tokens_in += tin
            state.usage_tokens_out += tout
            data = llm.extract_json(content)
            state.urgency = _enum(Urgency, data.get("urgency"), Urgency.medium)
            state.sentiment = _enum(Sentiment, data.get("sentiment"), Sentiment.neutral)
            state.topic = _enum(Topic, data.get("topic"), Topic.other)
            if data.get("escalate_reason"):
                state.escalate_reason = str(data["escalate_reason"])
            if data.get("pii_flags"):
                state.pii_flags = list({*state.pii_flags, *map(str, data["pii_flags"])})
            state.add_audit("triage_llm", summary=data.get("summary"))
            return state
        except Exception as e:
            state.add_audit("triage_llm_fallback", error=str(e))

    # Rule-based fallback
    state.topic = _rule_topic(lower)
    state.sentiment = _rule_sentiment(lower)
    if not state.escalate_reason:
        state.urgency = _rule_urgency(lower, state.sentiment)
    state.add_audit(
        "triage_rules",
        urgency=state.urgency.value,
        sentiment=state.sentiment.value,
        topic=state.topic.value,
    )
    return state


def _enum(cls: Any, value: Any, default: Any) -> Any:
    try:
        return cls(str(value).lower())
    except Exception:
        return default


def _rule_topic(lower: str) -> Topic:
    rules = [
        (Topic.pricing, ("price", "pricing", "cost", "how much", "plan", "subscription", "billing")),
        (Topic.hours, ("hour", "open", "close", "timezone", "when are you", "business hours")),
        (Topic.order, ("order", "tracking", "shipment", "shipping", "delivery", "ord-")),
        (Topic.policy, ("refund", "return", "privacy", "policy", "cancel", "terms")),
        (Topic.troubleshoot, ("broken", "error", "not working", "bug", "issue", "help with", "widget")),
    ]
    for topic, keys in rules:
        if any(k in lower for k in keys):
            return topic
    return Topic.other


def _rule_sentiment(lower: str) -> Sentiment:
    if any(w in lower for w in ("furious", "worst", "hate", "scam", "lawsuit", "angry")):
        return Sentiment.angry
    if any(w in lower for w in ("frustrated", "disappointed", "upset", "terrible", "awful")):
        return Sentiment.negative
    if any(w in lower for w in ("thanks", "great", "love", "awesome", "appreciate")):
        return Sentiment.positive
    return Sentiment.neutral


def _rule_urgency(lower: str, sentiment: Sentiment) -> Urgency:
    if any(w in lower for w in ("urgent", "asap", "immediately", "right now", "emergency")):
        return Urgency.high
    if sentiment == Sentiment.angry:
        return Urgency.high
    if any(w in lower for w in ("refund", "charged twice", "payment failed", "outage")):
        return Urgency.high
    if any(w in lower for w in ("price", "hours", "how do i", "what is")):
        return Urgency.low
    return Urgency.medium
