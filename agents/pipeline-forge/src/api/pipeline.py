"""Analyze / lists / CRM API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ..models import AnalyzeRequest, ApplyCrmRequest
from ..orchestrator import PipelineForge
from .deps import rate_limiter, require_api_key, require_widget_or_api_key


class PlaybookNoteBody(BaseModel):
    note: str


def build_pipeline_router(agent: PipelineForge, cfg: dict) -> APIRouter:
    router = APIRouter(prefix="/v1", tags=["pipeline"])
    admin = require_api_key(cfg)
    widget = require_widget_or_api_key(cfg)
    limit = int((cfg.get("rate_limit") or {}).get("analyze_per_minute") or 30)

    @router.post("/analyze")
    async def analyze(body: AnalyzeRequest, request: Request, _: None = Depends(widget)):
        rate_limiter.check(f"pf:{request.client.host if request.client else 'x'}", limit)
        run = agent.analyze(
            body.opportunities or None,
            cadence=body.cadence,
            source=body.source or "payload",
            metadata=body.metadata,
        )
        return run.model_dump()

    @router.post("/demo")
    async def demo(_: None = Depends(widget)):
        return agent.demo().model_dump()

    @router.get("/runs")
    async def list_runs(status: str | None = None, _: None = Depends(admin)):
        return {"items": [r.model_dump() for r in agent.store.list(status=status)]}

    @router.get("/runs/{run_id}")
    async def get_run(run_id: str, _: None = Depends(admin)):
        run = agent.store.get(run_id)
        if not run:
            raise HTTPException(404, "Run not found")
        return run.model_dump()

    @router.get("/priority")
    async def priority(_: None = Depends(admin)):
        latest = agent.store.latest_list()
        return latest or {"items": []}

    @router.post("/crm/apply")
    async def crm_apply(body: ApplyCrmRequest, _: None = Depends(admin)):
        run = agent.apply_crm(body.run_id, body.update_indexes or None)
        if not run:
            raise HTTPException(404, "Run not found")
        return run.model_dump()

    @router.get("/scoring")
    async def scoring(_: None = Depends(admin)):
        return {"scoring": cfg.get("scoring") or {}, "playbook": agent.playbook.context()}

    @router.post("/playbook/notes")
    async def playbook_note(body: PlaybookNoteBody, _: None = Depends(admin)):
        if not body.note.strip():
            raise HTTPException(400, "note required")
        return agent.playbook.add_note(body.note)

    return router
