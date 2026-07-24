"""Content generate / ideas / jobs API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from ..models import GenerateRequest, IdeaRequest, PublishRequest, ScheduleRequest
from ..orchestrator import ContentForge
from .deps import rate_limiter, require_api_key, require_widget_or_api_key


def build_content_router(agent: ContentForge, cfg: dict) -> APIRouter:
    router = APIRouter(prefix="/v1", tags=["content"])
    admin = require_api_key(cfg)
    gen_auth = require_widget_or_api_key(cfg)
    limit = int((cfg.get("rate_limit") or {}).get("generate_per_minute") or 20)

    @router.post("/generate")
    async def generate(
        body: GenerateRequest,
        request: Request,
        _: None = Depends(gen_auth),
    ):
        rate_limiter.check(f"gen:{request.client.host if request.client else 'x'}", limit)
        if not body.source_text.strip():
            raise HTTPException(400, "source_text required")
        job = agent.generate(
            body.source_text,
            source_title=body.source_title,
            goal=body.goal,
            audience=body.audience,
            metadata=body.metadata,
        )
        return job.model_dump()

    @router.post("/ideas")
    async def ideas(body: IdeaRequest, _: None = Depends(gen_auth)):
        return agent.suggest_ideas(body.business_input, count=body.count)

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
        return agent.schedule(
            body.job_id,
            run_at=body.run_at,
            channel=body.channel,
            content_key=body.content_key,
        )

    @router.get("/schedule")
    async def list_schedule(_: None = Depends(admin)):
        return {"items": agent.store.list_schedule()}

    @router.get("/brand")
    async def brand(_: None = Depends(admin)):
        from ..config import brand_voice_text

        return {
            "voice": brand_voice_text(cfg),
            "config": cfg.get("brand") or {},
        }

    return router
