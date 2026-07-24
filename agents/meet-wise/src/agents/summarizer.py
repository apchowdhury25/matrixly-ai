"""Summarizer agent."""

from __future__ import annotations

import re
from typing import Any

from .. import llm
from ..config import prompt_text
from ..models import Meeting, MeetingStatus


def run_summarizer(meeting: Meeting, cfg: dict) -> tuple[Meeting, int, int]:
    tin = tout = 0
    text = meeting.transcript[: int((cfg.get("meeting") or {}).get("max_transcript_chars") or 80000)]

    if llm.grok_available(cfg):
        try:
            system = prompt_text("summarizer")
            user = f"Platform: {meeting.platform.value}\nTitle: {meeting.title}\n\nTranscript:\n{text}"
            content, tin, tout = llm.chat(cfg, system, user)
            data = llm.extract_json(content)
            if isinstance(data, dict):
                _apply_summary(meeting, data)
            meeting.status = MeetingStatus.summarized
            return meeting, tin, tout
        except Exception as e:
            meeting.metadata["summarizer_error"] = str(e)

    _apply_summary(meeting, _rule_summary(text, meeting))
    meeting.status = MeetingStatus.summarized
    return meeting, tin, tout


def _apply_summary(meeting: Meeting, data: dict[str, Any]) -> None:
    if data.get("title"):
        meeting.title = str(data["title"])
    meeting.summary = str(data.get("summary") or "")
    meeting.decisions = [str(x) for x in (data.get("decisions") or [])]
    meeting.discussion_points = [str(x) for x in (data.get("discussion_points") or [])]
    meeting.risks = [str(x) for x in (data.get("risks_or_blockers") or data.get("risks") or [])]
    if data.get("participants"):
        meeting.participants = [str(x) for x in data["participants"]]
    if data.get("next_meeting"):
        meeting.next_meeting = str(data["next_meeting"])


def _rule_summary(text: str, meeting: Meeting) -> dict[str, Any]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    title = meeting.title
    for ln in lines[:5]:
        if ln.lower().startswith("meeting:"):
            title = ln.split(":", 1)[1].strip()
            break

    speakers = []
    for ln in lines:
        m = re.match(r"^([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)\s*:", ln)
        if m and m.group(1) not in speakers:
            speakers.append(m.group(1))

    decisions = []
    discussion = []
    for ln in lines:
        low = ln.lower()
        if any(k in low for k in ("decision", "agreed", "we start", "we'll", "we will", "approved")):
            decisions.append(ln[:240])
        elif ":" in ln and len(ln) > 40:
            discussion.append(ln[:240])

    discussion = discussion[:8]
    decisions = decisions[:6] or ["Review transcript for explicit decisions"]

    body = " ".join(ln for ln in lines if ":" in ln)[:500]
    summary = (
        f"Meeting on {meeting.meeting_date or 'recent date'} covered pilot scope and next steps. "
        f"{body[:320]}"
    )
    return {
        "title": title or "Meeting recap",
        "summary": summary,
        "decisions": decisions,
        "discussion_points": discussion or lines[3:8],
        "risks_or_blockers": [ln for ln in lines if "blocker" in ln.lower() or "legal" in ln.lower()][:3],
        "participants": speakers or meeting.participants,
        "next_meeting": None,
    }
