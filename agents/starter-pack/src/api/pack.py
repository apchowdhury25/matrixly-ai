"""Starter Pack API — overview, settings, agent controls."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..pack import StarterPack
from .deps import require_api_key


class ToggleBody(BaseModel):
    enabled: bool


class ConnectionsBody(BaseModel):
    connections: dict


def build_pack_router(pack: StarterPack, cfg: dict) -> APIRouter:
    router = APIRouter(prefix="/v1", tags=["pack"])
    auth = require_api_key(cfg)

    @router.get("/overview")
    async def overview(_: None = Depends(auth)):
        return pack.overview().model_dump()

    @router.get("/agents")
    async def agents(_: None = Depends(auth)):
        ov = pack.overview()
        return {"items": [a.model_dump() for a in ov.agents]}

    @router.get("/agents/{agent_id}")
    async def agent_detail(agent_id: str, _: None = Depends(auth)):
        ov = pack.overview()
        for a in ov.agents:
            if a.id == agent_id:
                adapter = pack.adapters.get(agent_id)
                return {
                    **a.model_dump(),
                    "audit": adapter.audit(limit=25) if adapter else [],
                    "hitl": adapter.hitl_pending() if adapter else [],
                    "usage": adapter.usage() if adapter else {},
                }
        raise HTTPException(404, "Unknown agent")

    @router.post("/agents/{agent_id}/toggle")
    async def toggle(agent_id: str, body: ToggleBody, _: None = Depends(auth)):
        if agent_id not in pack.adapters:
            raise HTTPException(404, "Unknown agent")
        s = pack.set_agent_enabled(agent_id, body.enabled)
        return s.model_dump()

    @router.get("/activity")
    async def activity(limit: int = 40, _: None = Depends(auth)):
        ov = pack.overview()
        return {"items": [a.model_dump() for a in ov.activity[:limit]]}

    @router.get("/analytics")
    async def analytics(_: None = Depends(auth)):
        return pack.overview().analytics

    @router.get("/settings")
    async def settings(_: None = Depends(auth)):
        s = pack.settings.load()
        return {
            **s.model_dump(),
            "connection_schema": cfg.get("connections") or {},
            "agent_runtime": {
                k: {"url": v.get("url"), "enabled": v.get("enabled")}
                for k, v in (cfg.get("agent_runtime") or {}).items()
                if isinstance(v, dict)
            },
        }

    @router.post("/settings/connections")
    async def save_connections(body: ConnectionsBody, _: None = Depends(auth)):
        s = pack.update_connections(body.connections)
        return s.model_dump()

    @router.get("/embed-snippets")
    async def embed_snippets(_: None = Depends(auth)):
        ov = pack.overview()
        out = {}
        for a in ov.agents:
            if a.id == "supportforge":
                out["supportforge"] = _widget_snippet(a.url, "SupportForge")
            if a.id == "bookwise":
                out["bookwise"] = _widget_snippet(a.url, "BookWise")
            if a.id == "invoiceforge":
                out["invoiceforge"] = {
                    "iframe": (
                        f'<iframe src="{a.url}/static/dashboard/index.html" '
                        f'title="InvoiceForge" style="width:100%;min-height:700px;border:1px solid #1e2a3a;border-radius:12px;"></iframe>'
                    )
                }
        out["starter_dashboard"] = {
            "iframe": (
                f'<iframe src="/static/dashboard/index.html" title="Matrixly Starter Pack" '
                f'style="width:100%;min-height:800px;border:1px solid #1e2a3a;border-radius:12px;"></iframe>'
            )
        }
        return out

    return router


def _widget_snippet(base_url: str, title: str) -> dict:
    base = base_url.rstrip("/")
    return {
        "script": (
            f'<script src="{base}/static/widget/embed.js"\n'
            f'  data-api="{base}"\n'
            f'  data-key="pk_live_your-site-key"\n'
            f'  async></script>'
        ),
        "iframe": (
            f'<iframe src="{base}/static/widget/chat-panel.html"\n'
            f'  title="{title}"\n'
            f'  style="width:100%;min-height:560px;border:1px solid #1e2a3a;border-radius:12px;"></iframe>'
        ),
    }
