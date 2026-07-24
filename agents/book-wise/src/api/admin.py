"""Admin dashboard API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..models import BookingStatus
from ..orchestrator import BookWise
from .deps import require_api_key


class DecideBody(BaseModel):
    note: str | None = None
    decided_by: str = "admin"


def build_admin_router(agent: BookWise, cfg: dict) -> APIRouter:
    router = APIRouter(prefix="/v1/admin", tags=["admin"])
    auth = require_api_key(cfg)

    @router.get("/status")
    async def status(_: None = Depends(auth)):
        return agent.status()

    @router.get("/bookings/upcoming")
    async def upcoming(_: None = Depends(auth)):
        items = agent.bookings.list(upcoming_only=True, limit=100)
        return {"items": [b.model_dump() for b in items]}

    @router.get("/bookings")
    async def bookings(status: str | None = None, _: None = Depends(auth)):
        items = agent.bookings.list(status=status, limit=100)
        return {"items": [b.model_dump() for b in items]}

    @router.get("/bookings/{booking_id}")
    async def booking_detail(booking_id: str, _: None = Depends(auth)):
        b = agent.bookings.get(booking_id)
        if not b:
            raise HTTPException(404, "Booking not found")
        return b.model_dump()

    @router.get("/hitl")
    async def hitl_pending(_: None = Depends(auth)):
        return {"items": [a.model_dump() for a in agent.hitl.list_pending()]}

    @router.post("/hitl/{action_id}/approve")
    async def approve(action_id: str, body: DecideBody | None = None, _: None = Depends(auth)):
        body = body or DecideBody()
        action = agent.hitl.decide(
            action_id, approve=True, decided_by=body.decided_by, note=body.note
        )
        if not action:
            raise HTTPException(404, "HITL action not found")
        if action.booking_id:
            b = agent.bookings.get(action.booking_id)
            if b and b.status == BookingStatus.pending_hitl:
                b.status = BookingStatus.confirmed
                b.calendar_event_id = agent.calendar.create_event(b)
                rems = agent.reminders.schedule_for_booking(b)
                b.reminders_scheduled = [r["id"] for r in rems]
                b.confirmation_sent = True
                agent.bookings.save(b)
        agent.audit.write("hitl_approved", action_id=action_id)
        return action.model_dump()

    @router.post("/hitl/{action_id}/reject")
    async def reject(action_id: str, body: DecideBody | None = None, _: None = Depends(auth)):
        body = body or DecideBody()
        action = agent.hitl.decide(
            action_id, approve=False, decided_by=body.decided_by, note=body.note
        )
        if not action:
            raise HTTPException(404, "HITL action not found")
        if action.booking_id:
            agent.bookings.cancel(action.booking_id, reason="HITL rejected")
        agent.audit.write("hitl_rejected", action_id=action_id)
        return action.model_dump()

    @router.get("/usage")
    async def usage(days: int = 30, _: None = Depends(auth)):
        return agent.usage.summary(days=days)

    @router.get("/audit")
    async def audit(limit: int = 100, _: None = Depends(auth)):
        return {"items": agent.audit.recent(limit=limit)}

    @router.get("/reminders/due")
    async def reminders_due(_: None = Depends(auth)):
        return {"items": agent.reminders.due()}

    return router
