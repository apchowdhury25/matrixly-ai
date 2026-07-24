"""Admin dashboard API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..orchestrator import InvoiceForge
from .deps import require_api_key


class DecideBody(BaseModel):
    note: str | None = None
    decided_by: str = "admin"


def build_admin_router(agent: InvoiceForge, cfg: dict) -> APIRouter:
    router = APIRouter(prefix="/v1/admin", tags=["admin"])
    auth = require_api_key(cfg)

    @router.get("/status")
    async def status(_: None = Depends(auth)):
        return agent.status()

    @router.get("/hitl")
    async def hitl_pending(_: None = Depends(auth)):
        return {"items": [a.model_dump() for a in agent.hitl.list_pending()]}

    @router.post("/hitl/{action_id}/approve")
    async def approve(action_id: str, body: DecideBody | None = None, _: None = Depends(auth)):
        body = body or DecideBody()
        inv = agent.approve_hitl(action_id, decided_by=body.decided_by)
        if not inv:
            raise HTTPException(404, "HITL action not found")
        return inv.model_dump()

    @router.post("/hitl/{action_id}/reject")
    async def reject(action_id: str, body: DecideBody | None = None, _: None = Depends(auth)):
        body = body or DecideBody()
        inv = agent.reject_hitl(action_id, decided_by=body.decided_by)
        if not inv:
            raise HTTPException(404, "HITL action not found")
        return inv.model_dump()

    @router.get("/usage")
    async def usage(days: int = 30, _: None = Depends(auth)):
        return agent.usage.summary(days=days)

    @router.get("/audit")
    async def audit(limit: int = 100, _: None = Depends(auth)):
        return {"items": agent.audit.recent(limit=limit)}

    @router.get("/report")
    async def report(_: None = Depends(auth)):
        return agent.report()

    @router.post("/reminders/process")
    async def reminders(_: None = Depends(auth)):
        n = agent.process_reminders()
        return {"sent": n}

    return router
