"""LangGraph-style multi-agent orchestrator for SupportForge."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .agents.escalation import run_escalation
from .agents.knowledge import run_knowledge
from .agents.responder import run_responder
from .agents.triage import run_triage
from .integrations.tickets import TicketStore
from .llm import cost_usd
from .memory.session_store import SessionStore
from .memory.vector_store import VectorStore
from .models import (
    ActionType,
    Channel,
    ChatMessage,
    Customer,
    SupportState,
    new_id,
)
from .services.audit import AuditLog
from .services.followup import FollowupQueue
from .services.hitl import HitlQueue
from .services.usage import UsageMeter


class SupportForge:
    """End-to-end support pipeline with HITL and audit."""

    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg
        data = Path(cfg["paths"]["data"])
        self.sessions = SessionStore(data)
        self.vectors = VectorStore(data)
        self.tickets = TicketStore(data, cfg)
        self.hitl = HitlQueue(data)
        self.followups = FollowupQueue(data)
        self.audit = AuditLog(data)
        self.usage = UsageMeter(data, cfg)

    def seed_knowledge(self) -> dict[str, Any]:
        kb = self.cfg.get("knowledge") or {}
        knowledge_dir = Path(self.cfg["paths"]["knowledge"])
        result = self.vectors.index_directory(
            knowledge_dir,
            chunk_size=int(kb.get("chunk_size") or 600),
            overlap=int(kb.get("chunk_overlap") or 80),
        )
        self.audit.write("kb_reindex", **result)
        return result

    def process(
        self,
        text: str,
        *,
        channel: Channel | str = Channel.chat,
        session_id: str | None = None,
        customer: Customer | None = None,
        subject: str = "",
        metadata: dict[str, Any] | None = None,
        create_ticket: bool = True,
    ) -> SupportState:
        if isinstance(channel, str):
            channel = Channel(channel)

        session = self.sessions.get_or_create(
            session_id, customer=customer, metadata=metadata
        )
        sid = session["session_id"]
        hist = self.sessions.history(sid)

        state = SupportState(
            message_id=new_id("msg_"),
            session_id=sid,
            channel=channel,
            customer=customer or Customer(**(session.get("customer") or {})),
            text=text.strip(),
            subject=subject or "",
            history=hist,
            metadata=metadata or {},
        )
        self.sessions.append_messages(
            sid, [ChatMessage(role="user", content=state.text)]
        )

        # 1) Triage
        state = run_triage(state, self.cfg)

        # Open or attach ticket early for non-chat or when useful
        if create_ticket and not state.ticket_id:
            t = self.tickets.create(
                subject=subject or state.text[:80] or "Support chat",
                channel=channel.value,
                customer=state.customer,
                body=state.text,
                tags=[state.topic.value],
                metadata={"session_id": sid},
            )
            state.ticket_id = t.id

        # Force escalate path
        force = bool(state.escalate_reason) or state.urgency.value == "critical"

        # 2) Knowledge
        if not force:
            state = run_knowledge(state, self.cfg, self.vectors)
        else:
            state = run_knowledge(state, self.cfg, self.vectors)
            state.add_audit("force_escalate", reason=state.escalate_reason)

        # 3) Responder
        state = run_responder(state, self.cfg)

        # 4) Decide action
        state.action = self._decide_action(state, force=force)

        if state.action == ActionType.escalate:
            state = run_escalation(
                state, self.cfg, self.tickets, self.hitl, self.followups
            )
        elif state.action == ActionType.draft_for_approval:
            action = self.hitl.enqueue(
                kind="publish_reply",
                payload={
                    "reply": state.answer,
                    "original": state.text,
                    "confidence": state.confidence,
                    "channel": channel.value,
                },
                ticket_id=state.ticket_id,
                session_id=sid,
            )
            state.hitl_id = action.id
            state.requires_human = True
            # Soften customer message for email; chat still shows draft
            if channel != Channel.chat:
                state.answer = (
                    "Thanks — I've prepared a reply for our team to review and send shortly."
                )
            state.add_audit("draft_queued", hitl_id=action.id)
        else:
            # auto_reply — still log; external email send would need HITL per mode
            if channel in (Channel.email,) and self._hitl_external():
                action = self.hitl.enqueue(
                    kind="send_email",
                    payload={"reply": state.answer, "to": state.customer.email},
                    ticket_id=state.ticket_id,
                    session_id=sid,
                )
                state.hitl_id = action.id
                state.add_audit("email_send_queued", hitl_id=action.id)

        # Persist assistant message + ticket update
        self.sessions.append_messages(
            sid,
            [
                ChatMessage(
                    role="assistant",
                    content=state.answer,
                )
            ],
        )
        if state.ticket_id:
            self.tickets.add_message(
                state.ticket_id,
                role="assistant",
                content=state.answer,
                meta={
                    "confidence": state.confidence,
                    "action": state.action.value,
                    "citations": [h.model_dump() for h in state.kb_hits],
                },
            )
            self.tickets.update_fields(
                state.ticket_id,
                confidence=state.confidence,
                topic=state.topic.value,
                urgency=state.urgency.value,
                sentiment=state.sentiment.value,
                citations=[h.model_dump() for h in state.kb_hits],
            )

        state.estimated_cost_usd = round(
            cost_usd(self.cfg, state.usage_tokens_in, state.usage_tokens_out), 6
        )
        usage_row = self.usage.record(
            channel=channel.value,
            session_id=sid,
            tokens_in=state.usage_tokens_in,
            tokens_out=state.usage_tokens_out,
            action=state.action.value,
            message_id=state.message_id,
        )
        for ev in state.audit_events:
            self.audit.write(
                ev.get("event", "pipeline"),
                message_id=state.message_id,
                session_id=sid,
                **{k: v for k, v in ev.items() if k not in {"event", "ts"}},
            )
        self.audit.write(
            "pipeline_complete",
            message_id=state.message_id,
            session_id=sid,
            action=state.action.value,
            confidence=state.confidence,
            ticket_id=state.ticket_id,
            cost=usage_row["estimated_cost_usd"],
        )
        return state

    def _decide_action(self, state: SupportState, force: bool = False) -> ActionType:
        th = self.cfg.get("thresholds") or {}
        auto_t = float(th.get("auto_resolve", 0.75))
        draft_t = float(th.get("draft_for_approval", 0.45))
        allowed = set(self.cfg.get("auto_reply_topics") or [])

        if force or state.escalate_reason:
            return ActionType.escalate
        if state.urgency.value == "critical":
            return ActionType.escalate
        if state.confidence < draft_t:
            return ActionType.escalate
        if state.confidence >= auto_t and state.topic.value in allowed:
            if state.channel == Channel.chat:
                return ActionType.auto_reply
            # email/form: prefer draft unless HITL off
            mode = (self.cfg.get("hitl") or {}).get("mode") or "external_only"
            if mode == "off" or (self.cfg.get("hitl") or {}).get("auto_approve"):
                return ActionType.auto_reply
            return ActionType.draft_for_approval
        if state.confidence >= draft_t:
            return ActionType.draft_for_approval
        return ActionType.escalate

    def _hitl_external(self) -> bool:
        hitl = self.cfg.get("hitl") or {}
        if hitl.get("auto_approve"):
            return False
        mode = hitl.get("mode") or "external_only"
        return mode in {"always", "external_only"}

    def status(self) -> dict[str, Any]:
        from . import llm as llm_mod

        return {
            "version": "1.0.0",
            "business": (self.cfg.get("business") or {}).get("name"),
            "grok": llm_mod.grok_available(self.cfg),
            "kb": self.vectors.stats(),
            "pending_hitl": len(self.hitl.list_pending()),
            "open_escalations": len(self.tickets.list_escalated()),
            "usage": self.usage.summary(days=7),
        }
