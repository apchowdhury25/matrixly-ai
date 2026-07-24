"""Booking Agent — confirm, reschedule, cancel with intake checks."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from ..integrations.calendar import CalendarService
from ..models import Booking, BookingState, BookingStatus, new_id
from ..services.bookings import BookingStore
from ..services.hitl import HitlQueue
from ..services.reminders import ReminderService


def missing_intake(state: BookingState, cfg: dict) -> list[str]:
    fields = cfg.get("intake_fields") or []
    missing: list[str] = []
    cust = state.customer
    values = {
        "name": cust.name,
        "email": cust.email,
        "phone": cust.phone,
        "notes": (state.metadata or {}).get("notes") or state.text,
    }
    for f in fields:
        if not f.get("required"):
            continue
        key = f.get("key")
        if key == "notes":
            continue  # optional for auto-flow
        if not values.get(key):
            missing.append(key)
    return missing


def run_book(
    state: BookingState,
    cfg: dict,
    calendar: CalendarService,
    store: BookingStore,
    reminders: ReminderService,
    hitl: HitlQueue,
) -> BookingState:
    if not state.selected_slot and state.proposals:
        # Auto-pick best if user said "first available" etc.
        lower = (state.text or "").lower()
        if any(
            w in lower
            for w in (
                "first",
                "earliest",
                "any slot",
                "whatever",
                "book it",
                "that works",
                "first available",
                "book #1",
                "book 1",
                "slot 1",
                "#1",
            )
        ):
            state.selected_slot = state.proposals[0].start_iso
        # Numeric choice "1".."5" handled in orchestrator; also "book 2"
        m = re.search(r"\b(?:book\s*#?|slot\s*#?|#)\s*(\d)\b", lower)
        if m and not state.selected_slot:
            idx = int(m.group(1)) - 1
            if 0 <= idx < len(state.proposals):
                state.selected_slot = state.proposals[idx].start_iso

    if not state.selected_slot:
        if not state.proposals:
            from .availability import run_availability

            state = run_availability(state, calendar)
        if state.proposals:
            lines = "\n".join(f"• {p.label}" for p in state.proposals)
            state.reply = (
                f"Here are the best open slots for "
                f"{calendar.service_meta(state.service_id).get('name', 'your appointment')}:\n\n"
                f"{lines}\n\n"
                f"Reply with a time (or say “first available”) and share your name + email to confirm."
            )
            state.add_audit("book_awaiting_slot")
            return state
        state.reply = (
            "I couldn't find open times in the next two weeks that match your request. "
            "A teammate will follow up — or try a different day."
        )
        state.requires_human = True
        action = hitl.enqueue(
            kind="no_availability",
            payload={"text": state.text, "service_id": state.service_id},
            session_id=state.session_id,
        )
        state.hitl_id = action.id
        return state

    missing = missing_intake(state, cfg)
    state.intake_missing = missing
    if missing:
        need = ", ".join(missing)
        state.reply = (
            f"Great — I can hold that time once I have your {need}. "
            f"Please reply with the missing details."
        )
        state.add_audit("book_awaiting_intake", missing=missing)
        return state

    # Edge case → HITL
    if state.edge_case:
        return _queue_edge(state, cfg, calendar, store, hitl)

    return _confirm(state, cfg, calendar, store, reminders)


def _confirm(
    state: BookingState,
    cfg: dict,
    calendar: CalendarService,
    store: BookingStore,
    reminders: ReminderService,
) -> BookingState:
    meta = calendar.service_meta(state.service_id)
    duration = int(meta.get("duration_minutes") or 30)
    start = datetime.fromisoformat(state.selected_slot.replace("Z", "+00:00"))
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    end = start + timedelta(minutes=duration)
    tz = calendar.business_tz()

    booking = Booking(
        id=new_id("bk_"),
        status=BookingStatus.confirmed,
        service_id=state.service_id,
        service_name=str(meta.get("name") or "Consultation"),
        start_iso=start.isoformat(),
        end_iso=end.isoformat(),
        timezone=tz,
        customer=state.customer,
        notes=(state.metadata or {}).get("notes") or "",
        intake={
            "name": state.customer.name,
            "email": state.customer.email,
            "phone": state.customer.phone,
        },
        channel=state.channel.value,
        session_id=state.session_id,
        confirmation_sent=True,
    )
    event_id = calendar.create_event(booking)
    booking.calendar_event_id = event_id
    rems = reminders.schedule_for_booking(booking)
    booking.reminders_scheduled = [r["id"] for r in rems]
    store.create(booking)

    state.booking = booking
    state.booking_id = booking.id
    local_label = start.astimezone(__import__("zoneinfo").ZoneInfo(tz)).strftime(
        "%a %b %d · %I:%M %p %Z"
    )
    biz = (cfg.get("business") or {}).get("name") or "us"
    state.reply = (
        f"You're booked with {biz}!\n\n"
        f"• Service: {booking.service_name}\n"
        f"• When: {local_label}\n"
        f"• Booking ID: {booking.id}\n"
        f"• Confirmation: sent to {booking.customer.email or 'your chat'}\n\n"
        f"I'll send reminders before your appointment to reduce no-shows. "
        f"Need to change it? Say reschedule or cancel and include your booking ID."
    )
    state.add_audit("booked", booking_id=booking.id, start=booking.start_iso)
    return state


def _queue_edge(
    state: BookingState,
    cfg: dict,
    calendar: CalendarService,
    store: BookingStore,
    hitl: HitlQueue,
) -> BookingState:
    meta = calendar.service_meta(state.service_id)
    duration = int(meta.get("duration_minutes") or 30)
    start = datetime.fromisoformat(state.selected_slot.replace("Z", "+00:00"))
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    end = start + timedelta(minutes=duration)
    booking = Booking(
        id=new_id("bk_"),
        status=BookingStatus.pending_hitl,
        service_id=state.service_id,
        service_name=str(meta.get("name") or "Consultation"),
        start_iso=start.isoformat(),
        end_iso=end.isoformat(),
        timezone=calendar.business_tz(),
        customer=state.customer,
        channel=state.channel.value,
        session_id=state.session_id,
        metadata={"edge_case": state.edge_case},
    )
    store.create(booking)
    action = hitl.enqueue(
        kind="edge_booking",
        payload={
            "edge_case": state.edge_case,
            "start_iso": booking.start_iso,
            "customer": state.customer.model_dump(),
            "text": state.text,
        },
        booking_id=booking.id,
        session_id=state.session_id,
    )
    state.booking = booking
    state.booking_id = booking.id
    state.hitl_id = action.id
    state.requires_human = True
    state.reply = (
        "Thanks — this request needs a quick human review "
        f"({state.edge_case}). I've reserved a pending booking ({booking.id}) "
        "and a teammate will confirm shortly."
    )
    state.add_audit("edge_hitl", hitl_id=action.id, booking_id=booking.id)
    return state


def run_reschedule(
    state: BookingState,
    calendar: CalendarService,
    store: BookingStore,
    reminders: ReminderService,
) -> BookingState:
    booking = None
    if state.booking_id:
        booking = store.get(state.booking_id)
    elif state.customer.email:
        found = store.find_by_email(state.customer.email)
        booking = found[0] if found else None

    if not booking:
        state.reply = (
            "I couldn't find an active booking to reschedule. "
            "Please share your booking ID (bk_…) or the email used to book."
        )
        return state

    if not state.selected_slot:
        state.service_id = booking.service_id
        from .availability import run_availability

        state = run_availability(state, calendar)
        if state.proposals:
            lines = "\n".join(f"• {p.label}" for p in state.proposals)
            state.reply = (
                f"I found booking {booking.id}. Pick a new time:\n\n{lines}\n\n"
                f"Reply with the time you prefer."
            )
            state.booking_id = booking.id
            return state
        state.reply = "No alternate slots found right now. Please try another day."
        return state

    # Apply reschedule
    meta = calendar.service_meta(booking.service_id)
    duration = int(meta.get("duration_minutes") or 30)
    start = datetime.fromisoformat(state.selected_slot.replace("Z", "+00:00"))
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    end = start + timedelta(minutes=duration)

    calendar.delete_event(booking)
    reminders.cancel_for_booking(booking.id)
    booking.start_iso = start.isoformat()
    booking.end_iso = end.isoformat()
    booking.status = BookingStatus.confirmed
    booking.calendar_event_id = calendar.create_event(booking)
    rems = reminders.schedule_for_booking(booking)
    booking.reminders_scheduled = [r["id"] for r in rems]
    store.save(booking)

    state.booking = booking
    state.reply = (
        f"Rescheduled {booking.id} to {booking.start_iso}. "
        f"Updated calendar + reminders are in place."
    )
    state.add_audit("rescheduled", booking_id=booking.id)
    return state


def run_cancel(
    state: BookingState,
    calendar: CalendarService,
    store: BookingStore,
    reminders: ReminderService,
) -> BookingState:
    booking = None
    if state.booking_id:
        booking = store.get(state.booking_id)
    elif state.customer.email:
        found = store.find_by_email(state.customer.email)
        booking = found[0] if found else None

    if not booking:
        state.reply = (
            "I couldn't find a booking to cancel. Share your booking ID or email."
        )
        return state

    calendar.delete_event(booking)
    reminders.cancel_for_booking(booking.id)
    store.cancel(booking.id, reason=state.text[:200])
    booking = store.get(booking.id)
    state.booking = booking
    state.reply = (
        f"Cancelled booking {booking.id if booking else ''}. "
        f"Sorry we won't meet this time — reply anytime to rebook."
    )
    state.add_audit("cancelled", booking_id=state.booking_id or (booking.id if booking else None))
    return state
