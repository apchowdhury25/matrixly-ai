"""Admin API."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..orchestrator import ETFAnalyzer
from .deps import require_api_key


def build_admin_router(agent: ETFAnalyzer, cfg: dict) -> APIRouter:
    router = APIRouter(prefix="/v1/admin", tags=["admin"])
    auth = require_api_key(cfg)

    @router.get("/status")
    async def status(_: None = Depends(auth)):
        return agent.status()

    @router.get("/audit")
    async def audit(limit: int = 50, _: None = Depends(auth)):
        return {"items": agent.audit.recent(limit=limit)}

    @router.get("/usage")
    async def usage(_: None = Depends(auth)):
        return agent.usage.summary()

    return router
