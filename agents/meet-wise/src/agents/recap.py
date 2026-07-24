"""Recap email agent."""

from __future__ import annotations

from .. import llm
from ..config import prompt_text
from ..models import Meeting, MeetingStatus


def run_recap(meeting: Meeting, cfg: dict) -> tuple[Meeting, int, int]:
    tin = tout = 0
    prefix = (cfg.get("email") or {}).get("subject_prefix") or "[Meeting recap]"

    if llm.grok_available(cfg):
        try:
            system = prompt_text("recap")
            user = (
                f"Title: {meeting.title}\n"
                f"Participants: {meeting.participants}\n"
                f"Summary: {meeting.summary}\n"
                f"Decisions: {meeting.decisions}\n"
                f"Actions: {[a.model_dump() for a in meeting.action_items]}\n"
                f"Follow-ups: {meeting.follow_ups}"
            )
            content, tin, tout = llm.chat(cfg, system, user, temperature=0.3)
            data = llm.extract_json(content)
            if isinstance(data, dict):
                meeting.recap_subject = str(data.get("subject") or f"{prefix} {meeting.title}")
                meeting.recap_body = str(data.get("body_markdown") or "")
            meeting.status = MeetingStatus.recap_drafted
            return meeting, tin, tout
        except Exception as e:
            meeting.metadata["recap_error"] = str(e)

    meeting.recap_subject = f"{prefix} {meeting.title or 'Team meeting'}"
    actions = "\n".join(
        f"- {a.description} (owner: {a.owner or 'TBD'}, due: {a.deadline or 'TBD'})"
        for a in meeting.action_items
    )
    decisions = "\n".join(f"- {d}" for d in meeting.decisions) or "- (none captured)"
    meeting.recap_body = (
        f"Hi team,\n\n"
        f"Thanks for joining **{meeting.title or 'our meeting'}**.\n\n"
        f"## Summary\n{meeting.summary}\n\n"
        f"## Decisions\n{decisions}\n\n"
        f"## Action items\n{actions}\n\n"
    )
    if meeting.follow_ups:
        meeting.recap_body += "## Follow-ups flagged\n" + "\n".join(f"- {f}" for f in meeting.follow_ups) + "\n\n"
    meeting.recap_body += "Best regards,\nMatrixly MeetWise\n"
    meeting.status = MeetingStatus.recap_drafted
    return meeting, tin, tout
