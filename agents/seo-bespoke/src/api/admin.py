"""Admin routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..orchestrator import SEOBespoke
from .deps import require_api_key


def build_admin_router(agent: SEOBespoke, cfg: dict) -> APIRouter:
    router = APIRouter(prefix="/v1/admin", tags=["admin"])
    admin = require_api_key(cfg)

    @router.get("/usage")
    async def usage(_: None = Depends(admin)):
        return agent.usage.summary()

    @router.get("/health-detail")
    async def health_detail(_: None = Depends(admin)):
        return {
            "status": agent.status(),
            "graph_waves": agent.executor.waves,
        }

    return router
