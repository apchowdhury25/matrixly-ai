"""Reply agent — brand-voice draft replies."""

from __future__ import annotations

from typing import Any

from .. import llm
from ..config import prompt_text
from ..memory.brand import BrandMemory
from ..models import InboxItem


def run_replies(
    items: list[InboxItem],
    cfg: dict,
    brand: BrandMemory,
) -> tuple[list[InboxItem], int, int]:
    tin = tout = 0
    if not items:
        return items, 0, 0

    if llm.grok_available(cfg):
        try:
            system = prompt_text("reply") + "\n\n# Brand voice\n" + brand.context_block()
            payload = [i.model_dump() for i in items]
            user = f"Draft replies for:\n{payload}"
            content, tin, tout = llm.chat(cfg, system, user)
            data = llm.extract_json(content)
            if isinstance(data, dict):
                _apply(items, data)
                return items, tin, tout
        except Exception:
            pass

    _apply(items, _rule_replies(items, cfg))
    return items, tin, tout


def _apply(items: list[InboxItem], data: dict[str, Any]) -> None:
    by_id = {str(r.get("inbox_id")): r for r in (data.get("replies") or [])}
    for item in items:
        raw = by_id.get(item.id)
        if not raw and (data.get("replies") or []):
            # match by order if ids missing
            idx = items.index(item)
            replies = data.get("replies") or []
            raw = replies[idx] if idx < len(replies) else None
        if not raw:
            continue
        item.draft_reply = str(raw.get("draft") or "")
        item.reply_tone = str(raw.get("tone") or "helpful")
        item.escalate = bool(raw.get("escalate"))
        item.status = "draft_ready"


def _rule_replies(items: list[InboxItem], cfg: dict) -> dict[str, Any]:
    site = (cfg.get("business") or {}).get("website") or "https://matrixly.world"
    replies = []
    for item in items:
        text = item.text.lower()
        escalate = item.sentiment == "negative" and any(
            w in text for w in ("refund", "legal", "lawyer", "sue")
        )
        if "buffer" in text:
            draft = (
                f"Yes — SocialForge can export to Buffer (and local queue). "
                f"You approve posts before anything ships. Happy to share setup steps."
            )
        elif "instagram" in text:
            draft = (
                f"Instagram captions are first-class — compose, schedule, and review in one calendar. "
                f"Meta Graph connect is optional for publish."
            )
        elif "pric" in text:
            draft = (
                f"Thanks for asking! You can explore free on {site}/pricing — "
                f"Starter is great for small teams. Want a short walkthrough?"
            )
        elif "voice" in text or "spam" in text:
            draft = (
                "Brand voice lives in persistent memory (voice.md + notes) and every draft "
                "goes through human approval before posting. You're always in control."
            )
        elif item.sentiment == "positive":
            draft = "Thanks so much — glad it resonated! What are you automating next?"
        else:
            draft = (
                f"Appreciate you reaching out. SocialForge helps SMBs draft, schedule, and reply "
                f"in brand voice with human approval. Learn more at {site}."
            )
        replies.append(
            {
                "inbox_id": item.id,
                "draft": draft,
                "tone": "apologetic" if item.sentiment == "negative" else "helpful",
                "escalate": escalate,
            }
        )
    return {"replies": replies}
