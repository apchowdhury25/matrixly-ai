"""Knowledge base admin endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from ..integrations.notion_kb import sync_notion_database
from ..models import KbUpload
from ..orchestrator import SupportForge
from .deps import require_api_key


def build_kb_router(forge: SupportForge, cfg: dict) -> APIRouter:
    router = APIRouter(prefix="/v1/kb", tags=["kb"])
    auth = require_api_key(cfg)

    @router.post("/reindex")
    async def reindex(_: None = Depends(auth)):
        return forge.seed_knowledge()

    @router.post("/upload")
    async def upload(body: KbUpload, _: None = Depends(auth)):
        knowledge = Path(cfg["paths"]["knowledge"])
        knowledge.mkdir(parents=True, exist_ok=True)
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in body.title)[:80]
        path = knowledge / f"{safe}.md"
        path.write_text(f"# {body.title}\n\n{body.content}\n", encoding="utf-8")
        stats = forge.seed_knowledge()
        return {"ok": True, "path": str(path.name), "index": stats}

    @router.post("/notion-sync")
    async def notion_sync(_: None = Depends(auth)):
        result = sync_notion_database(cfg, cfg["paths"]["knowledge"])
        if not result.get("ok"):
            raise HTTPException(400, result.get("reason") or "Notion sync failed")
        stats = forge.seed_knowledge()
        return {"notion": result, "index": stats}

    @router.get("/stats")
    async def stats(_: None = Depends(auth)):
        return forge.vectors.stats()

    return router
