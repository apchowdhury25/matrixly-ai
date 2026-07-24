"""Admin dashboard API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..orchestrator import SupportForge
from .deps import require_api_key


class DecideBody(BaseModel):
    note: str | None = None
    decided_by: str = "admin"


def build_admin_router(forge: SupportForge, cfg: dict) -> APIRouter:
    router = APIRouter(prefix="/v1/admin", tags=["admin"])
    auth = require_api_key(cfg)

    @router.get("/escalations")
    async def escalations(_: None = Depends(auth)):
        tickets = forge.tickets.list_escalated()
        return {"items": [t.model_dump() for t in tickets]}

    @router.get("/tickets")
    async def tickets(status: str | None = None, _: None = Depends(auth)):
        items = forge.tickets.list(status=status)
        return {"items": [t.model_dump() for t in items]}

    @router.get("/tickets/{ticket_id}")
    async def ticket_detail(ticket_id: str, _: None = Depends(auth)):
        t = forge.tickets.get(ticket_id)
        if not t:
            raise HTTPException(404, "Ticket not found")
        return t.model_dump()

    @router.get("/hitl")
    async def hitl_pending(_: None = Depends(auth)):
        return {"items": [a.model_dump() for a in forge.hitl.list_pending()]}

    @router.post("/hitl/{action_id}/approve")
    async def approve(action_id: str, body: DecideBody | None = None, _: None = Depends(auth)):
        body = body or DecideBody()
        action = forge.hitl.decide(
            action_id, approve=True, decided_by=body.decided_by, note=body.note
        )
        if not action:
            raise HTTPException(404, "HITL action not found or already decided")
        forge.audit.write("hitl_approved", action_id=action_id, by=body.decided_by)
        # Apply side effects for known kinds
        if action.kind == "publish_reply" and action.ticket_id:
            forge.tickets.add_message(
                action.ticket_id,
                role="agent",
                content=str((action.payload or {}).get("reply") or ""),
                meta={"hitl_id": action_id, "approved": True},
            )
        return action.model_dump()

    @router.post("/hitl/{action_id}/reject")
    async def reject(action_id: str, body: DecideBody | None = None, _: None = Depends(auth)):
        body = body or DecideBody()
        action = forge.hitl.decide(
            action_id, approve=False, decided_by=body.decided_by, note=body.note
        )
        if not action:
            raise HTTPException(404, "HITL action not found or already decided")
        forge.audit.write("hitl_rejected", action_id=action_id, by=body.decided_by)
        return action.model_dump()

    @router.get("/usage")
    async def usage(days: int = 30, _: None = Depends(auth)):
        return forge.usage.summary(days=days)

    @router.get("/audit")
    async def audit(limit: int = 100, _: None = Depends(auth)):
        return {"items": forge.audit.recent(limit=limit)}

    @router.get("/status")
    async def status(_: None = Depends(auth)):
        return forge.status()

    return router
