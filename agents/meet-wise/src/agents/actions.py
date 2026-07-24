"""Action item extractor."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

from .. import llm
from ..config import prompt_text
from ..models import ActionItem, Meeting, MeetingStatus


def run_actions(meeting: Meeting, cfg: dict) -> tuple[Meeting, int, int]:
    tin = tout = 0
    text = meeting.transcript[:60000]

    if llm.grok_available(cfg):
        try:
            system = prompt_text("actions")
            user = f"Transcript:\n{text}\n\nSummary:\n{meeting.summary}"
            content, tin, tout = llm.chat(cfg, system, user)
            data = llm.extract_json(content)
            if isinstance(data, dict):
                meeting.action_items = [
                    ActionItem(**_normalize_action(a, cfg))
                    for a in (data.get("action_items") or [])
                    if isinstance(a, dict)
                ]
                meeting.follow_ups = [str(x) for x in (data.get("follow_ups") or [])]
            meeting.status = MeetingStatus.actions_extracted
            _flag_items(meeting, cfg)
            return meeting, tin, tout
        except Exception as e:
            meeting.metadata["actions_error"] = str(e)

    meeting.action_items, meeting.follow_ups = _rule_actions(text, cfg)
    _flag_items(meeting, cfg)
    meeting.status = MeetingStatus.actions_extracted
    return meeting, tin, tout


def _normalize_action(a: dict[str, Any], cfg: dict) -> dict[str, Any]:
    return {
        "description": str(a.get("description") or "Action item"),
        "owner": a.get("owner"),
        "deadline": a.get("deadline"),
        "priority": str(a.get("priority") or "normal"),
        "source_quote": str(a.get("source_quote") or "")[:200],
        "flagged": False,
    }


def _flag_items(meeting: Meeting, cfg: dict) -> None:
    actions_cfg = cfg.get("actions") or {}
    require_owner = actions_cfg.get("require_owner", True)
    flag_deadline = actions_cfg.get("flag_missing_deadline", True)
    for item in meeting.action_items:
        if require_owner and not item.owner:
            item.flagged = True
            meeting.follow_ups.append(f"Missing owner: {item.description[:80]}")
        if flag_deadline and not item.deadline:
            item.flagged = True
            meeting.follow_ups.append(f"Missing deadline: {item.description[:80]}")
    # dedupe follow_ups
    meeting.follow_ups = list(dict.fromkeys(meeting.follow_ups))


def _rule_actions(text: str, cfg: dict) -> tuple[list[ActionItem], list[str]]:
    items: list[ActionItem] = []
    follow: list[str] = []
    default_days = int((cfg.get("actions") or {}).get("default_due_days") or 3)
    default_due = (datetime.now(timezone.utc) + timedelta(days=default_days)).date().isoformat()

    patterns = [
        r"(?i)(?:owner for[^\.]+ is|([A-Z][a-z]+)\s+will|I'll|I will|([A-Z][a-z]+)\s+to)\s+([^\.]{10,120})",
        r"(?i)(deadline|by)\s+([A-Za-z]+\s+\d{1,2}|\d{4}-\d{2}-\d{2}|Friday|Monday)",
    ]
    for ln in text.splitlines():
        low = ln.lower()
        if any(k in low for k in ("i'll", "i will", "will create", "will send", "owner for", "follow-up", "follow up")):
            owner = None
            m = re.match(r"^([A-Z][a-zA-Z]+)\s*:", ln)
            if m:
                owner = m.group(1)
            else:
                m2 = re.search(r"\b([A-Z][a-z]{2,})\s+will\b", ln)
                if m2:
                    owner = m2.group(1)
            desc = re.sub(r"^[^:]+:\s*", "", ln).strip()[:200]
            items.append(
                ActionItem(
                    description=desc,
                    owner=owner,
                    deadline=default_due if "deadline" in low or "by " in low else None,
                    priority="high" if "asap" in low or "urgent" in low else "normal",
                    source_quote=ln[:160],
                )
            )
        if "follow-up" in low or "follow up" in low or "next week" in low:
            follow.append(ln[:200])

    if not items:
        items.append(
            ActionItem(
                description="Distribute meeting recap and confirm next steps",
                owner=None,
                deadline=default_due,
                priority="normal",
            )
        )
    return items[:12], follow[:8]
