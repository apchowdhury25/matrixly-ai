"""CRM mapping agent."""

from __future__ import annotations

from typing import Any

from .. import llm
from ..config import prompt_text
from ..models import Meeting, MeetingStatus


def run_crm_mapper(meeting: Meeting, cfg: dict) -> tuple[Meeting, int, int]:
    tin = tout = 0
    crm_cfg = cfg.get("crm") or {}
    owner_map = crm_cfg.get("owner_map") or {}

    if llm.grok_available(cfg):
        try:
            system = prompt_text("crm") + f"\n\nOwner map: {owner_map}"
            user = (
                f"Summary: {meeting.summary}\n"
                f"Decisions: {meeting.decisions}\n"
                f"Actions: {[a.model_dump() for a in meeting.action_items]}\n"
                f"Transcript excerpt:\n{meeting.transcript[:5000]}"
            )
            content, tin, tout = llm.chat(cfg, system, user)
            data = llm.extract_json(content)
            if isinstance(data, dict):
                meeting.crm_payload = _enrich_crm(data, meeting, cfg)
            meeting.status = MeetingStatus.crm_mapped
            return meeting, tin, tout
        except Exception as e:
            meeting.metadata["crm_error"] = str(e)

    meeting.crm_payload = _rule_crm(meeting, cfg)
    meeting.status = MeetingStatus.crm_mapped
    return meeting, tin, tout


def _enrich_crm(data: dict[str, Any], meeting: Meeting, cfg: dict) -> dict[str, Any]:
    owner_map = (cfg.get("crm") or {}).get("owner_map") or {}
    tasks = []
    for t in data.get("tasks") or []:
        if not isinstance(t, dict):
            continue
        owner = t.get("owner_email")
        if not owner and t.get("owner"):
            owner = owner_map.get(str(t.get("owner")))
        tasks.append(
            {
                "subject": t.get("subject") or "Meeting task",
                "owner_email": owner,
                "due_date": t.get("due_date"),
                "status": (cfg.get("crm") or {}).get("task_status") or "Not Started",
                "priority": (cfg.get("crm") or {}).get("task_priority") or "Normal",
                "description": t.get("description") or "",
            }
        )
    # Ensure action items become tasks
    for a in meeting.action_items:
        if not any(a.description[:40] in (t.get("subject") or "") for t in tasks):
            tasks.append(
                {
                    "subject": a.description[:120],
                    "owner_email": owner_map.get(a.owner or "") if a.owner else None,
                    "due_date": a.deadline,
                    "status": (cfg.get("crm") or {}).get("task_status") or "Not Started",
                    "priority": a.priority.title() if a.priority else "Normal",
                    "description": a.source_quote or a.description,
                }
            )
    opp = data.get("opportunity") or {}
    if not opp.get("stage"):
        opp["stage"] = (cfg.get("crm") or {}).get("opportunity_default_stage") or "Qualification"
    notes = data.get("notes") or [
        {"title": meeting.title or "Meeting notes", "body": meeting.summary}
    ]
    return {"opportunity": opp, "tasks": tasks, "notes": notes}


def _rule_crm(meeting: Meeting, cfg: dict) -> dict[str, Any]:
    crm = cfg.get("crm") or {}
    owner_map = crm.get("owner_map") or {}
    keywords = [k.lower() for k in (crm.get("opportunity_keywords") or [])]
    blob = (meeting.summary + " " + " ".join(meeting.decisions)).lower()
    make_opp = any(k in blob for k in keywords) or "pilot" in blob or "deal" in blob

    opp = {}
    if make_opp:
        name = "Meeting follow-up opportunity"
        for d in meeting.decisions:
            if "pilot" in d.lower() or "opportunity" in d.lower():
                name = d[:80]
                break
        opp = {
            "name": name,
            "stage": crm.get("opportunity_default_stage") or "Qualification",
            "amount": None,
            "next_step": meeting.action_items[0].description if meeting.action_items else "Follow up",
            "notes": meeting.summary,
        }

    tasks = []
    for a in meeting.action_items:
        tasks.append(
            {
                "subject": a.description[:120],
                "owner_email": owner_map.get(a.owner or "") if a.owner else None,
                "due_date": a.deadline,
                "status": crm.get("task_status") or "Not Started",
                "priority": (a.priority or "normal").title(),
                "description": a.source_quote or a.description,
            }
        )

    notes = [
        {
            "title": meeting.title or "Meeting notes",
            "body": meeting.summary
            + "\n\nDecisions:\n"
            + "\n".join(f"- {d}" for d in meeting.decisions),
        }
    ]
    return {"opportunity": opp, "tasks": tasks, "notes": notes}
