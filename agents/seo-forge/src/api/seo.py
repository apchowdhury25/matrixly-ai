"""SEOForge public/workspace API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from ..models import (
    AuditRequest,
    BrandVoiceUpdate,
    ChatRequest,
    GenerateRequest,
    KeywordUpsert,
    LocalSeoRequest,
    OnboardRequest,
    PlanRequest,
    PublishRequest,
    RoiEvent,
    ScheduleRequest,
)
from ..orchestrator import SEOForge
from .deps import rate_limiter, require_api_key, require_widget_or_api_key


def build_seo_router(agent: SEOForge, cfg: dict) -> APIRouter:
    router = APIRouter(prefix="/v1", tags=["seo"])
    admin = require_api_key(cfg)
    gen_auth = require_widget_or_api_key(cfg)
    gen_limit = int((cfg.get("rate_limit") or {}).get("generate_per_minute") or 30)
    chat_limit = int((cfg.get("rate_limit") or {}).get("chat_per_minute") or 40)

    @router.post("/chat")
    async def chat(body: ChatRequest, request: Request, _: None = Depends(gen_auth)):
        rate_limiter.check(f"chat:{request.client.host if request.client else 'x'}", chat_limit)
        if not body.message.strip():
            raise HTTPException(400, "message required")
        return agent.chat(body.message, session_id=body.session_id, profile=body.profile or None)

    @router.post("/onboard")
    async def onboard(body: OnboardRequest, _: None = Depends(gen_auth)):
        return agent.onboard(body.model_dump())

    @router.post("/plan")
    async def plan(body: PlanRequest, request: Request, _: None = Depends(gen_auth)):
        rate_limiter.check(f"gen:{request.client.host if request.client else 'x'}", gen_limit)
        if not body.business_input.strip():
            raise HTTPException(400, "business_input required")
        job = agent.create_plan(
            body.business_input,
            primary_goal=body.primary_goal,
            service_areas=body.service_areas,
            business_type=body.business_type,
        )
        return job.model_dump()

    @router.post("/generate")
    async def generate(body: GenerateRequest, request: Request, _: None = Depends(gen_auth)):
        rate_limiter.check(f"gen:{request.client.host if request.client else 'x'}", gen_limit)
        if not body.brief.strip():
            raise HTTPException(400, "brief required")
        job = agent.generate_content(
            body.brief,
            content_type=body.content_type,
            primary_keyword=body.primary_keyword,
            service_areas=body.service_areas,
            goal=body.goal,
            title=body.title,
            metadata=body.metadata,
        )
        return job.model_dump()

    @router.post("/audit")
    async def audit(body: AuditRequest, request: Request, _: None = Depends(gen_auth)):
        rate_limiter.check(f"gen:{request.client.host if request.client else 'x'}", gen_limit)
        if not body.page_text.strip():
            raise HTTPException(400, "page_text required")
        job = agent.audit_page(
            body.page_text,
            url_or_title=body.url_or_title,
            primary_keyword=body.primary_keyword,
        )
        return job.model_dump()

    @router.post("/local")
    async def local(body: LocalSeoRequest, request: Request, _: None = Depends(gen_auth)):
        rate_limiter.check(f"gen:{request.client.host if request.client else 'x'}", gen_limit)
        if not body.business_input.strip():
            raise HTTPException(400, "business_input required")
        job = agent.local_package(
            body.business_input,
            service_areas=body.service_areas,
            gbp_notes=body.gbp_notes,
        )
        return job.model_dump()

    @router.get("/jobs")
    async def list_jobs(status: str | None = None, _: None = Depends(admin)):
        return {"items": [j.model_dump() for j in agent.store.list(status=status)]}

    @router.get("/jobs/{job_id}")
    async def get_job(job_id: str, _: None = Depends(admin)):
        job = agent.store.get(job_id)
        if not job:
            raise HTTPException(404, "Job not found")
        return job.model_dump()

    @router.post("/publish")
    async def publish(body: PublishRequest, _: None = Depends(admin)):
        return agent.publish(body.job_id, targets=body.targets)

    @router.post("/schedule")
    async def schedule(body: ScheduleRequest, _: None = Depends(admin)):
        return agent.schedule(body.job_id, run_at=body.run_at, channel=body.channel)

    @router.get("/schedule")
    async def list_schedule(_: None = Depends(admin)):
        return {"items": agent.store.list_schedule()}

    @router.get("/keywords")
    async def keywords(_: None = Depends(gen_auth)):
        return {"items": agent.keywords.list(), "summary": agent.keywords.summary()}

    @router.post("/keywords")
    async def keywords_upsert(body: KeywordUpsert, _: None = Depends(admin)):
        items = agent.keywords.upsert(body.keywords)
        return {"items": items, "summary": agent.keywords.summary()}

    @router.delete("/keywords")
    async def keywords_delete(keyword: str, city: str = "", _: None = Depends(admin)):
        ok = agent.keywords.remove(keyword, city=city)
        if not ok:
            raise HTTPException(404, "Keyword not found")
        return {"ok": True, "summary": agent.keywords.summary()}

    @router.get("/brand")
    async def brand_get(_: None = Depends(gen_auth)):
        return {
            "voice": agent.brand.get_voice(),
            "profile": agent.brand.get_profile(),
            "config": cfg.get("brand") or {},
        }

    @router.put("/brand")
    async def brand_put(body: BrandVoiceUpdate, _: None = Depends(admin)):
        result = agent.brand.save_voice(
            body.voice_markdown,
            tone=body.tone,
            avoid=body.avoid,
        )
        return result

    @router.get("/roi")
    async def roi_get(_: None = Depends(gen_auth)):
        return {
            "summary": agent.roi.summary(),
            "events": agent.roi.events(40),
            "keywords": agent.keywords.summary(),
        }

    @router.post("/roi")
    async def roi_post(body: RoiEvent, _: None = Depends(admin)):
        row = agent.roi.record(
            hours_saved=body.hours_saved,
            leads_attributed=body.leads_attributed,
            revenue_usd=body.revenue_usd,
            note=body.note,
            job_id=body.job_id or "",
            source="manual",
        )
        return {"ok": True, "event": row, "summary": agent.roi.summary()}

    return router
