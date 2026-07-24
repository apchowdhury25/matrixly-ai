"""Structured booking API + webhooks."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..models import (
    BookRequest,
    CancelRequest,
    Channel,
    Customer,
    FormWebhook,
    RescheduleRequest,
)
from ..orchestrator import BookWise
from .deps import require_api_key


def build_bookings_router(agent: BookWise, cfg: dict) -> APIRouter:
    router = APIRouter(prefix="/v1", tags=["bookings"])
    auth = require_api_key(cfg)

    @router.get("/availability")
    async def availability(
        service_id: str = "consult",
        preferred_date: str | None = None,
        preferred_time: str | None = None,
        _: None = Depends(auth),
    ):
        slots = agent.calendar.propose_slots(
            service_id=service_id,
            preferred_date=preferred_date,
            preferred_time=preferred_time,
        )
        return {"items": [s.model_dump() for s in slots]}

    @router.post("/bookings")
    async def book(body: BookRequest, _: None = Depends(auth)):
        # Structured book: set intake via process flow
        text = (
            f"Please book me for service {body.service_id} at {body.start_iso}. "
            f"My name is {body.customer.name or 'Guest'} and email is {body.customer.email or ''}."
        )
        if body.notes:
            text += f" Notes: {body.notes}"
        state = agent.process(
            text,
            channel=body.channel,
            session_id=body.session_id,
            customer=body.customer,
            selected_slot=body.start_iso,
            service_id=body.service_id,
            metadata={"notes": body.notes, **body.intake},
        )
        if not state.booking:
            raise HTTPException(400, state.reply or "Could not book")
        return state.booking.model_dump()

    @router.post("/bookings/reschedule")
    async def reschedule(body: RescheduleRequest, _: None = Depends(auth)):
        state = agent.process(
            f"Reschedule {body.booking_id} to {body.new_start_iso}",
            channel=Channel.api,
            booking_id=body.booking_id,
            selected_slot=body.new_start_iso,
        )
        if not state.booking:
            raise HTTPException(400, state.reply)
        return state.booking.model_dump()

    @router.post("/bookings/cancel")
    async def cancel(body: CancelRequest, _: None = Depends(auth)):
        state = agent.process(
            f"Cancel {body.booking_id}. {body.reason}",
            channel=Channel.api,
            booking_id=body.booking_id,
        )
        if not state.booking:
            raise HTTPException(404, state.reply)
        return state.booking.model_dump()

    @router.post("/webhooks/form")
    async def form_hook(body: FormWebhook, _: None = Depends(auth)):
        text = body.message or "I'd like to book an appointment."
        if body.preferred_time:
            text += f" Preferred: {body.preferred_time}."
        state = agent.process(
            text,
            channel=Channel.form,
            customer=Customer(name=body.name, email=body.email, phone=body.phone),
            service_id=body.service_id or "consult",
            metadata=body.metadata,
        )
        return {
            "ok": True,
            "session_id": state.session_id,
            "reply": state.reply,
            "proposals": [p.model_dump() for p in state.proposals],
            "booking": state.booking.model_dump() if state.booking else None,
        }

    @router.post("/webhooks/email")
    async def email_hook(payload: dict, _: None = Depends(auth)):
        from_email = str(payload.get("from_email") or "")
        from_name = payload.get("from_name")
        subject = str(payload.get("subject") or "")
        body = str(payload.get("body") or "")
        text = f"Subject: {subject}\n\n{body}" if subject else body
        state = agent.process(
            text,
            channel=Channel.email,
            customer=Customer(name=from_name, email=from_email),
        )
        return {
            "ok": True,
            "reply": state.reply,
            "booking_id": state.booking_id,
            "intent": state.intent.value,
        }

    return router
