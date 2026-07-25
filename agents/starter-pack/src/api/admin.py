"""Admin status / audit / usage for the pack."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..pack import StarterPack
from .deps import require_api_key


def build_admin_router(pack: StarterPack, cfg: dict) -> APIRouter:
    router = APIRouter(prefix="/v1/admin", tags=["admin"])
    auth = require_api_key(cfg)

    @router.get("/status")
    async def status(_: None = Depends(auth)):
        return pack.status()

    @router.get("/audit")
    async def audit(limit: int = 100, _: None = Depends(auth)):
        return {"items": pack.audit.recent(limit=limit)}

    @router.get("/usage")
    async def usage(_: None = Depends(auth)):
        return pack.usage.summary()

    return router
