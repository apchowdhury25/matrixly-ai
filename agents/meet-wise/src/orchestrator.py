"""LangGraph-style meeting pipeline: summarize → actions → CRM → recap → HITL."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .agents.actions import run_actions
from .agents.crm_mapper import run_crm_mapper
from .agents.recap import run_recap
from .agents.summarizer import run_summarizer
from .integrations.crm import CrmWriter
from .integrations.email_out import RecapMailer
from .integrations.transcripts import load_upload
from .llm import cost_usd, grok_available
from .models import Meeting, MeetingStatus, Platform, new_id
from .services.audit import AuditLog
from .services.hitl import HitlQueue
from .services.store import MeetingStore
from .services.usage import UsageMeter


class MeetWise:
    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg
        data = Path(cfg["paths"]["data"])
        self.store = MeetingStore(data)
        self.hitl = HitlQueue(data)
        self.audit = AuditLog(data)
        self.usage = UsageMeter(data, cfg)
        self.crm = CrmWriter(data, cfg)
        self.mailer = RecapMailer(data, cfg)
        self.samples = Path(cfg["paths"]["samples"])

    def process(
        self,
        transcript: str,
        *,
        title: str = "",
        platform: Platform | str = Platform.upload,
        meeting_date: str | None = None,
        participants: list[str] | None = None,
        source_file: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Meeting:
        if isinstance(platform, str):
            try:
                platform = Platform(platform)
            except Exception:
                platform = Platform.other

        meeting = Meeting(
            id=new_id("mtg_"),
            status=MeetingStatus.received,
            platform=platform,
            title=title,
            meeting_date=meeting_date,
            participants=participants or [],
            transcript=transcript.strip(),
            source_file=source_file,
            metadata=metadata or {},
        )
        self.store.save(meeting)
        self.audit.write("received", meeting_id=meeting.id, platform=platform.value)

        tin = tout = 0
        meeting, a, b = run_summarizer(meeting, self.cfg)
        tin += a
        tout += b
        self.store.save(meeting)
        self.audit.write("summarized", meeting_id=meeting.id)

        meeting, a, b = run_actions(meeting, self.cfg)
        tin += a
        tout += b
        self.store.save(meeting)
        self.audit.write("actions", meeting_id=meeting.id, count=len(meeting.action_items))

        meeting, a, b = run_crm_mapper(meeting, self.cfg)
        tin += a
        tout += b
        self.store.save(meeting)
        self.audit.write("crm_mapped", meeting_id=meeting.id)

        meeting, a, b = run_recap(meeting, self.cfg)
        tin += a
        tout += b
        meeting.usage_tokens_in = tin
        meeting.usage_tokens_out = tout
        meeting.estimated_cost_usd = round(cost_usd(self.cfg, tin, tout), 6)
        self.store.export(meeting)

        # HITL for CRM + email
        hitl = self.cfg.get("hitl") or {}
        mode = hitl.get("mode") or "external_only"
        auto = hitl.get("auto_approve")
        needs_review = mode != "off" and not auto and (
            hitl.get("review_crm_writes", True) or hitl.get("review_recap_email", True)
        )
        if needs_review:
            action = self.hitl.enqueue(
                kind="meeting_apply",
                payload={
                    "title": meeting.title,
                    "actions": len(meeting.action_items),
                    "follow_ups": meeting.follow_ups,
                    "crm_tasks": len((meeting.crm_payload or {}).get("tasks") or []),
                    "recap_subject": meeting.recap_subject,
                },
                meeting_id=meeting.id,
            )
            meeting.hitl_id = action.id
            meeting.status = MeetingStatus.pending_review
            self.audit.write("hitl_queued", meeting_id=meeting.id, hitl_id=action.id)
        else:
            self._apply(meeting)
            meeting.status = MeetingStatus.applied

        self.store.save(meeting)
        self.usage.record(
            action="process",
            tokens_in=tin,
            tokens_out=tout,
            meeting_id=meeting.id,
        )
        self.audit.write("pipeline_complete", meeting_id=meeting.id, status=meeting.status.value)
        return meeting

    def process_file(self, path: str | Path) -> Meeting:
        data = load_upload(path)
        return self.process(
            data["transcript"],
            platform=data.get("platform") or "upload",
            source_file=data.get("filename"),
        )

    def _apply(self, meeting: Meeting) -> None:
        crm_res = self.crm.apply(meeting)
        meeting.crm_applied = bool(crm_res.get("ok"))
        mail_res = self.mailer.send(meeting, to_addrs=[])
        meeting.email_sent = bool(mail_res.get("ok"))
        meeting.metadata["crm_result"] = crm_res
        meeting.metadata["email_result"] = mail_res
        self.audit.write("applied", meeting_id=meeting.id, crm=crm_res, email=mail_res)

    def approve(self, hitl_id: str, decided_by: str = "admin") -> Meeting | None:
        action = self.hitl.decide(hitl_id, approve=True, decided_by=decided_by)
        if not action or not action.meeting_id:
            return None
        meeting = self.store.get(action.meeting_id)
        if not meeting:
            return None
        self._apply(meeting)
        meeting.status = MeetingStatus.applied
        self.store.save(meeting)
        self.audit.write("approved", meeting_id=meeting.id, hitl_id=hitl_id)
        return meeting

    def reject(self, hitl_id: str, decided_by: str = "admin") -> Meeting | None:
        action = self.hitl.decide(hitl_id, approve=False, decided_by=decided_by)
        if not action or not action.meeting_id:
            return None
        meeting = self.store.get(action.meeting_id)
        if not meeting:
            return None
        meeting.status = MeetingStatus.rejected
        self.store.save(meeting)
        self.audit.write("rejected", meeting_id=meeting.id, hitl_id=hitl_id)
        return meeting

    def demo(self) -> Meeting:
        sample = self.samples / "demo_transcript.txt"
        text = sample.read_text(encoding="utf-8") if sample.exists() else "Alex: We agreed to start the pilot."
        return self.process(
            text,
            title="Matrixly Pilot Kickoff",
            platform=Platform.zoom,
            meeting_date="2026-07-20",
        )

    def status(self) -> dict[str, Any]:
        items = self.store.list(limit=100)
        return {
            "version": "1.0.0",
            "business": (self.cfg.get("business") or {}).get("name"),
            "grok": grok_available(self.cfg),
            "meetings": len(items),
            "pending_review": len([m for m in items if m.status == MeetingStatus.pending_review]),
            "pending_hitl": len(self.hitl.list_pending()),
            "meeting_backend": (self.cfg.get("meeting") or {}).get("backend"),
            "crm_backend": (self.cfg.get("crm") or {}).get("backend"),
            "usage": self.usage.summary(days=7),
        }
