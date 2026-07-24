"""LangGraph-style multi-agent orchestrator for BookWise."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .agents.availability import run_availability
from .agents.booking_agent import run_book, run_cancel, run_reschedule
from .agents.intent import run_intent
from .integrations.calendar import CalendarService
from .llm import cost_usd
from .memory.session_store import SessionStore
from .models import (
    BookingState,
    Channel,
    ChatMessage,
    Customer,
    Intent,
    new_id,
)
from .services.audit import AuditLog
from .services.bookings import BookingStore
from .services.hitl import HitlQueue
from .services.reminders import ReminderService
from .services.usage import UsageMeter


class BookWise:
    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg
        data = Path(cfg["paths"]["data"])
        self.sessions = SessionStore(data)
        self.bookings = BookingStore(data)
        self.hitl = HitlQueue(data)
        self.reminders = ReminderService(data, cfg)
        self.audit = AuditLog(data)
        self.usage = UsageMeter(data, cfg)
        self.calendar = CalendarService(cfg, self.bookings)

    def process(
        self,
        text: str,
        *,
        channel: Channel | str = Channel.chat,
        session_id: str | None = None,
        customer: Customer | None = None,
        selected_slot: str | None = None,
        service_id: str | None = None,
        booking_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> BookingState:
        if isinstance(channel, str):
            channel = Channel(channel)

        session = self.sessions.get_or_create(
            session_id, customer=customer, metadata=metadata
        )
        sid = session["session_id"]
        ctx = session.get("context") or {}
        hist = self.sessions.history(sid)

        state = BookingState(
            message_id=new_id("msg_"),
            session_id=sid,
            channel=channel,
            customer=customer or Customer(**(session.get("customer") or {})),
            text=(text or "").strip(),
            history=hist,
            service_id=service_id or ctx.get("service_id") or "consult",
            selected_slot=selected_slot,
            booking_id=booking_id or ctx.get("pending_booking_id"),
            timezone=(self.cfg.get("business") or {}).get("timezone") or "America/Chicago",
            metadata=metadata or {},
        )

        # Map numeric slot selection: "1", "2", ...
        if not state.selected_slot and state.text.isdigit():
            idx = int(state.text) - 1
            props = ctx.get("proposals") or []
            if 0 <= idx < len(props):
                state.selected_slot = props[idx].get("start_iso")

        # Match label / time phrase against stored proposals
        if not state.selected_slot and ctx.get("proposals"):
            lower = state.text.lower()
            for p in ctx["proposals"]:
                label = (p.get("label") or "").lower()
                start = p.get("start_iso") or ""
                if start and (start in state.text or label and label in lower):
                    state.selected_slot = start
                    break
                # "10:00" style match against label
                if any(tok in label for tok in lower.replace(".", "").split() if ":" in tok or tok.isdigit()):
                    if any(part in label for part in lower.split() if len(part) >= 3):
                        state.selected_slot = start
                        break

        self.sessions.append_messages(sid, [ChatMessage(role="user", content=state.text)])

        # 1) Intent
        state = run_intent(state, self.cfg)

        # If user is supplying intake after proposals, treat as book
        if state.intent in {Intent.intake, Intent.other} and (
            state.selected_slot or ctx.get("proposals")
        ):
            if state.customer.email or state.customer.name:
                state.intent = Intent.book
                if not state.selected_slot and ctx.get("proposals"):
                    # keep proposals for book flow
                    from .models import SlotProposal

                    state.proposals = [SlotProposal(**p) for p in ctx["proposals"]]

        # Restore proposals into state for booking
        if not state.proposals and ctx.get("proposals"):
            from .models import SlotProposal

            try:
                state.proposals = [SlotProposal(**p) for p in ctx["proposals"]]
            except Exception:
                pass

        # 2) Route by intent
        if state.intent in {Intent.availability, Intent.book} and not state.selected_slot:
            state = run_availability(state, self.calendar)
            if state.intent == Intent.availability:
                if state.proposals:
                    lines = "\n".join(
                        f"{i+1}. {p.label}" for i, p in enumerate(state.proposals)
                    )
                    biz_tz = state.timezone
                    state.reply = (
                        f"Here are open times ({biz_tz}), with buffers applied:\n\n"
                        f"{lines}\n\n"
                        f"Reply with a number, a time, or “book #1” plus your name and email."
                    )
                else:
                    state.reply = (
                        "No open slots match that window. Try another day, "
                        "or ask for morning/afternoon."
                    )
            else:
                state = run_book(
                    state,
                    self.cfg,
                    self.calendar,
                    self.bookings,
                    self.reminders,
                    self.hitl,
                )
        elif state.intent == Intent.book:
            if not state.proposals:
                state = run_availability(state, self.calendar)
            state = run_book(
                state,
                self.cfg,
                self.calendar,
                self.bookings,
                self.reminders,
                self.hitl,
            )
        elif state.intent == Intent.reschedule:
            state = run_reschedule(
                state, self.calendar, self.bookings, self.reminders
            )
        elif state.intent == Intent.cancel:
            state = run_cancel(state, self.calendar, self.bookings, self.reminders)
        elif state.intent == Intent.status:
            state = self._status(state)
        else:
            if not state.reply:
                state.reply = (
                    (self.cfg.get("channels") or {}).get("chat") or {}
                ).get("welcome") or (
                    "I can help you check availability, book, reschedule, or cancel. "
                    "What would you like to do?"
                )

        # Persist session context
        self.sessions.update_context(
            sid,
            service_id=state.service_id,
            proposals=[p.model_dump() for p in state.proposals],
            pending_booking_id=state.booking_id,
            last_intent=state.intent.value,
        )
        # Update customer on session
        session = self.sessions.get(sid) or {}
        session["customer"] = state.customer.model_dump()
        self.sessions.save(sid, session)

        self.sessions.append_messages(
            sid, [ChatMessage(role="assistant", content=state.reply)]
        )

        state.estimated_cost_usd = round(
            cost_usd(self.cfg, state.usage_tokens_in, state.usage_tokens_out), 6
        )
        self.usage.record(
            channel=channel.value,
            session_id=sid,
            tokens_in=state.usage_tokens_in,
            tokens_out=state.usage_tokens_out,
            action=state.intent.value,
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
            intent=state.intent.value,
            booking_id=state.booking_id,
        )
        return state

    def _status(self, state: BookingState) -> BookingState:
        items = []
        if state.booking_id:
            b = self.bookings.get(state.booking_id)
            if b:
                items = [b]
        elif state.customer.email:
            items = self.bookings.find_by_email(state.customer.email)
        if not items:
            state.reply = "I don't see an upcoming booking. Want to schedule one?"
            return state
        lines = []
        for b in items[:5]:
            lines.append(f"• {b.id}: {b.service_name} at {b.start_iso} ({b.status.value})")
        state.reply = "Your bookings:\n\n" + "\n".join(lines)
        state.booking = items[0]
        return state

    def status(self) -> dict[str, Any]:
        from . import llm as llm_mod

        upcoming = self.bookings.list(upcoming_only=True, limit=20)
        return {
            "version": "1.0.0",
            "business": (self.cfg.get("business") or {}).get("name"),
            "timezone": (self.cfg.get("business") or {}).get("timezone"),
            "calendar_backend": self.calendar.backend,
            "grok": llm_mod.grok_available(self.cfg),
            "upcoming_bookings": len(upcoming),
            "pending_hitl": len(self.hitl.list_pending()),
            "usage": self.usage.summary(days=7),
        }
