"""Intent Agent — classify booking requests."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .. import llm
from ..config import prompt_text
from ..models import BookingState, Intent

_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
_PHONE = re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
_BK = re.compile(r"\bbk_[a-f0-9]{8,}\b", re.I)


def run_intent(state: BookingState, cfg: dict) -> BookingState:
    text = state.text or ""
    lower = text.lower()

    # Edge keywords
    for kw in (cfg.get("hitl") or {}).get("edge_keywords") or []:
        if kw.lower() in lower:
            state.edge_case = kw
            break

    m = _EMAIL.search(text)
    if m and not state.customer.email:
        state.customer.email = m.group(0)
    m = _PHONE.search(text)
    if m and not state.customer.phone:
        state.customer.phone = m.group(0)
    m = _BK.search(text)
    if m:
        state.booking_id = m.group(0)
    # "My name is Alex Rivera" / "I'm Alex Rivera"
    if not state.customer.name:
        nm = re.search(
            r"(?:my name is|i am|i'm)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})",
            text,
            re.I,
        )
        if nm:
            state.customer.name = nm.group(1).strip()
        else:
            # "name is Alex Rivera"
            nm2 = re.search(
                r"\bname\s+is\s+([A-Za-z]+(?:\s+[A-Za-z]+){0,2})",
                text,
                re.I,
            )
            if nm2:
                state.customer.name = nm2.group(1).strip()

    if llm.grok_available(cfg):
        try:
            system = prompt_text("intent") or "Classify booking intent as JSON."
            content, tin, tout = llm.chat(cfg, system, f"Message:\n{text}")
            state.usage_tokens_in += tin
            state.usage_tokens_out += tout
            data = llm.extract_json(content)
            try:
                state.intent = Intent(str(data.get("intent") or "other").lower())
            except Exception:
                state.intent = Intent.other
            if data.get("service_id"):
                state.service_id = str(data["service_id"])
            if data.get("preferred_date"):
                state.preferred_date = str(data["preferred_date"])
            if data.get("preferred_time"):
                state.preferred_time = str(data["preferred_time"])
            if data.get("booking_ref"):
                state.booking_id = str(data["booking_ref"])
            if data.get("name") and not state.customer.name:
                state.customer.name = str(data["name"])
            if data.get("email") and not state.customer.email:
                state.customer.email = str(data["email"])
            if data.get("phone") and not state.customer.phone:
                state.customer.phone = str(data["phone"])
            if data.get("edge_case"):
                state.edge_case = str(data["edge_case"])
            state.add_audit("intent_llm", intent=state.intent.value, summary=data.get("summary"))
            return state
        except Exception as e:
            state.add_audit("intent_llm_fallback", error=str(e))

    state.intent = _rule_intent(lower)
    state.service_id = _rule_service(lower)
    state.preferred_date, state.preferred_time = _rule_when(lower, cfg)
    state.add_audit("intent_rules", intent=state.intent.value)
    return state


def _rule_intent(lower: str) -> Intent:
    if any(w in lower for w in ("cancel", "call off", "don't need", "do not need")):
        return Intent.cancel
    if any(w in lower for w in ("reschedule", "move my", "change my appointment", "different time")):
        return Intent.reschedule
    if any(w in lower for w in ("my appointment", "status", "confirm my", "when is my")):
        return Intent.status
    # Prefer book when user both asks to book and mentions availability ("first available")
    if any(
        w in lower
        for w in (
            "book",
            "schedule me",
            "schedule a",
            "set up a",
            "reserve",
            "meet with",
            "first available",
            "earliest",
            "book it",
            "book #",
            "book slot",
        )
    ):
        return Intent.book
    if any(
        w in lower
        for w in (
            "available",
            "availability",
            "openings",
            "when can",
            "free slots",
            "what times",
            "open times",
        )
    ):
        return Intent.availability
    if "appointment" in lower or "schedule" in lower:
        return Intent.book
    if any(w in lower for w in ("my name is", "email is", "my phone")):
        return Intent.intake
    return Intent.other


def _rule_service(lower: str) -> str:
    if "demo" in lower:
        return "demo"
    if "support" in lower:
        return "support"
    return "consult"


def _rule_when(lower: str, cfg: dict) -> tuple[str | None, str | None]:
    tz_name = (cfg.get("business") or {}).get("timezone") or "America/Chicago"
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo("UTC")
    now = datetime.now(tz)
    date = None
    time = None

    if "tomorrow" in lower:
        date = (now + timedelta(days=1)).date().isoformat()
    elif "today" in lower:
        date = now.date().isoformat()
    elif "next week" in lower:
        date = (now + timedelta(days=7)).date().isoformat()
    else:
        days = {
            "monday": 0,
            "tuesday": 1,
            "wednesday": 2,
            "thursday": 3,
            "friday": 4,
            "saturday": 5,
            "sunday": 6,
        }
        for name, idx in days.items():
            if name in lower:
                delta = (idx - now.weekday()) % 7
                if delta == 0:
                    delta = 7
                date = (now + timedelta(days=delta)).date().isoformat()
                break

    if "morning" in lower:
        time = "morning"
    elif "afternoon" in lower:
        time = "afternoon"
    else:
        m = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", lower)
        if m:
            h = int(m.group(1))
            mi = int(m.group(2) or 0)
            ap = m.group(3)
            if ap == "pm" and h < 12:
                h += 12
            if ap == "am" and h == 12:
                h = 0
            time = f"{h:02d}:{mi:02d}"

    return date, time
