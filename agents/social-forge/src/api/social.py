"""Compose / calendar / inbox API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ..models import ComposeRequest, MonitorRequest, PublishRequest, ReplyRequest, ScheduleRequest
from ..orchestrator import SocialForge
from .deps import rate_limiter, require_api_key, require_widget_or_api_key


class BrandNoteBody(BaseModel):
    note: str


def build_social_router(agent: SocialForge, cfg: dict) -> APIRouter:
    router = APIRouter(prefix="/v1", tags=["social"])
    admin = require_api_key(cfg)
    widget = require_widget_or_api_key(cfg)
    limit = int((cfg.get("rate_limit") or {}).get("generate_per_minute") or 30)

    @router.post("/compose")
    async def compose(body: ComposeRequest, request: Request, _: None = Depends(widget)):
        rate_limiter.check(f"sf:{request.client.host if request.client else 'x'}", limit)
        if not body.idea.strip():
            raise HTTPException(400, "idea required")
        c = agent.compose(
            body.idea,
            platforms=body.platforms or None,
            theme=body.theme,
            metadata=body.metadata,
        )
        return c.model_dump()

    @router.get("/campaigns")
    async def list_campaigns(status: str | None = None, _: None = Depends(admin)):
        return {"items": [c.model_dump() for c in agent.store.list_campaigns(status=status)]}

    @router.get("/campaigns/{campaign_id}")
    async def get_campaign(campaign_id: str, _: None = Depends(admin)):
        c = agent.store.get_campaign(campaign_id)
        if not c:
            raise HTTPException(404, "Campaign not found")
        return c.model_dump()

    @router.get("/calendar")
    async def calendar(_: None = Depends(admin)):
        return {"items": agent.store.list_schedule()}

    @router.post("/schedule")
    async def schedule(body: ScheduleRequest, _: None = Depends(admin)):
        c = agent.store.get_campaign(body.campaign_id)
        if not c:
            raise HTTPException(404, "Campaign not found")
        if body.platform not in c.posts:
            raise HTTPException(400, "platform not in campaign")
        c.posts[body.platform].scheduled_at = body.run_at
        item = {
            "campaign_id": c.id,
            "platform": body.platform,
            "suggested_at": body.run_at,
            "reason": "manual schedule",
        }
        agent.store.save_schedule_item(item)
        agent.store.save_campaign(c)
        return {"ok": True, "campaign": c.model_dump(), "slot": item}

    @router.post("/publish")
    async def publish(body: PublishRequest, _: None = Depends(admin)):
        c = agent.publish(
            body.campaign_id,
            platforms=body.platforms or None,
            backend=body.backend or None,
        )
        if not c:
            raise HTTPException(404, "Campaign not found")
        return c.model_dump()

    @router.post("/monitor")
    async def monitor(body: MonitorRequest | None = None, _: None = Depends(admin)):
        body = body or MonitorRequest()
        return agent.monitor(body.raw_items or None)

    @router.get("/inbox")
    async def inbox(status: str | None = None, _: None = Depends(admin)):
        return {"items": [i.model_dump() for i in agent.store.list_inbox(status=status)]}

    @router.post("/replies")
    async def replies(body: ReplyRequest | None = None, _: None = Depends(admin)):
        body = body or ReplyRequest()
        return agent.draft_replies(body.inbox_ids or None)

    @router.get("/insights")
    async def insights(_: None = Depends(admin)):
        latest = agent.store.latest_insights()
        if latest:
            return latest.model_dump()
        return agent.insights().model_dump()

    @router.post("/insights/refresh")
    async def insights_refresh(_: None = Depends(admin)):
        return agent.insights().model_dump()

    @router.get("/brand")
    async def brand(_: None = Depends(admin)):
        return {
            "voice_preview": agent.brand.voice()[:2000],
            "notes": agent.brand.notes(),
        }

    @router.post("/brand/notes")
    async def brand_note(body: BrandNoteBody, _: None = Depends(admin)):
        if not body.note.strip():
            raise HTTPException(400, "note required")
        return agent.brand.add_note(body.note)

    @router.post("/demo")
    async def demo(_: None = Depends(widget)):
        return agent.demo().model_dump()

    return router
