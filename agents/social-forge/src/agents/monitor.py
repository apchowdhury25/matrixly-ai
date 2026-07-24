"""Monitor agent — mentions, comments, DMs."""

from __future__ import annotations

from typing import Any

from .. import llm
from ..config import prompt_text
from ..models import InboxItem, new_id


def run_monitor(
    cfg: dict,
    raw_items: list[dict[str, Any]] | None = None,
) -> tuple[list[InboxItem], int, int, str]:
    tin = tout = 0
    items_in = raw_items if raw_items is not None else _demo_seed()

    if llm.grok_available(cfg) and items_in:
        try:
            system = prompt_text("monitor")
            user = f"Inbound social items JSON:\n{items_in}"
            content, tin, tout = llm.chat(cfg, system, user)
            data = llm.extract_json(content)
            if isinstance(data, dict):
                return _to_items(data), tin, tout, str(data.get("summary") or "")
        except Exception:
            pass

    data = _rule_monitor(items_in)
    return _to_items(data), tin, tout, str(data.get("summary") or "")


def _to_items(data: dict[str, Any]) -> list[InboxItem]:
    out: list[InboxItem] = []
    for raw in data.get("items") or []:
        iid = str(raw.get("id") or new_id("inb_"))
        out.append(
            InboxItem(
                id=iid,
                platform=str(raw.get("platform") or "x"),
                kind=str(raw.get("kind") or "comment"),
                author=str(raw.get("author") or "unknown"),
                text=str(raw.get("text") or ""),
                sentiment=str(raw.get("sentiment") or "neutral"),
                priority=str(raw.get("priority") or "normal"),
                needs_reply=bool(raw.get("needs_reply", True)),
                topic=str(raw.get("topic") or ""),
                status="open",
            )
        )
    return out


def _demo_seed() -> list[dict[str, Any]]:
    return [
        {
            "platform": "linkedin",
            "kind": "comment",
            "author": "Jordan Lee",
            "text": "Does this work with our existing Buffer queue?",
        },
        {
            "platform": "x",
            "kind": "mention",
            "author": "@ops_sara",
            "text": "@matrixly love the HITL approach — any Instagram support?",
        },
        {
            "platform": "instagram",
            "kind": "comment",
            "author": "localbiz_mike",
            "text": "Pricing?",
        },
        {
            "platform": "facebook",
            "kind": "dm",
            "author": "Alex R",
            "text": "We got a spammy draft — how do we keep brand voice locked?",
        },
    ]


def _rule_monitor(items: list[dict[str, Any]]) -> dict[str, Any]:
    out = []
    for raw in items:
        text = str(raw.get("text") or "").lower()
        sentiment = "neutral"
        priority = "normal"
        if any(w in text for w in ("love", "great", "thanks", "awesome")):
            sentiment = "positive"
        if any(w in text for w in ("spam", "angry", "broken", "refund", "hate")):
            sentiment = "negative"
            priority = "high"
        if any(w in text for w in ("pricing", "price", "cost", "demo", "buffer")):
            priority = "high" if priority != "high" else priority
            topic = "sales"
        else:
            topic = "general"
        if "instagram" in text:
            topic = "product"
        out.append(
            {
                "id": new_id("inb_"),
                "platform": raw.get("platform") or "x",
                "kind": raw.get("kind") or "comment",
                "author": raw.get("author") or "unknown",
                "text": raw.get("text") or "",
                "sentiment": sentiment,
                "priority": priority,
                "needs_reply": True,
                "topic": topic,
            }
        )
    return {
        "items": out,
        "summary": f"Classified {len(out)} inbound items (rule-based).",
    }
