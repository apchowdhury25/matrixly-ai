"""Public / workspace API for SEO-Bespoke."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from ..models import (
    BrandVoiceUpdate,
    ChatRequest,
    GeneratePackageRequest,
    HitlDecision,
    KeywordUpsert,
    QuizAnswers,
    QuizSubmitRequest,
    RoiEvent,
)
from ..orchestrator import SEOBespoke
from .deps import rate_limiter, require_api_key, require_widget_or_api_key


def build_bespoke_router(agent: SEOBespoke, cfg: dict) -> APIRouter:
    router = APIRouter(prefix="/v1", tags=["seo-bespoke"])
    admin = require_api_key(cfg)
    gen_auth = require_widget_or_api_key(cfg)
    gen_limit = int((cfg.get("rate_limit") or {}).get("generate_per_minute") or 20)
    quiz_limit = int((cfg.get("rate_limit") or {}).get("quiz_per_minute") or 40)

    @router.get("/graph")
    async def graph(_: None = Depends(gen_auth)):
        return agent.graph_describe()

    @router.get("/status")
    async def status(_: None = Depends(gen_auth)):
        return agent.status()

    @router.post("/chat")
    async def chat(body: ChatRequest, request: Request, _: None = Depends(gen_auth)):
        rate_limiter.check(f"chat:{request.client.host if request.client else 'x'}", quiz_limit)
        if not body.message.strip():
            raise HTTPException(400, "message required")
        return agent.chat(body.message, session_id=body.session_id, profile_id=body.profile_id)

    @router.post("/quiz/submit")
    async def quiz_submit(body: QuizSubmitRequest, request: Request, _: None = Depends(gen_auth)):
        rate_limiter.check(f"quiz:{request.client.host if request.client else 'x'}", gen_limit)
        if body.regenerate and body.profile_id:
            run = agent.regenerate_from_profile(body.profile_id)
        else:
            run = agent.run_full_pipeline(body.answers)
        return _run_response(run)

    @router.post("/generate")
    async def generate(body: GeneratePackageRequest, request: Request, _: None = Depends(gen_auth)):
        rate_limiter.check(f"gen:{request.client.host if request.client else 'x'}", gen_limit)
        if body.profile_id and not body.answers:
            run = agent.regenerate_from_profile(body.profile_id)
        elif body.answers:
            run = agent.run_full_pipeline(
                body.answers,
                existing_run_id=body.run_id,
            )
        else:
            raise HTTPException(400, "answers or profile_id required")
        return _run_response(run)

    @router.post("/demo")
    async def demo(request: Request, _: None = Depends(gen_auth)):
        rate_limiter.check(f"gen:{request.client.host if request.client else 'x'}", gen_limit)
        run = agent.demo()
        return _run_response(run)

    @router.get("/runs")
    async def list_runs(status: str | None = None, _: None = Depends(admin)):
        return {"items": [_run_response(r) for r in agent.list_runs(status=status)]}

    @router.get("/runs/{run_id}")
    async def get_run(run_id: str, _: None = Depends(gen_auth)):
        run = agent.get_run(run_id)
        if not run:
            raise HTTPException(404, "run not found")
        return _run_response(run)

    @router.get("/profiles")
    async def list_profiles(_: None = Depends(gen_auth)):
        return {"items": [p.model_dump() for p in agent.list_profiles()]}

    @router.get("/profiles/{profile_id}")
    async def get_profile(profile_id: str, _: None = Depends(gen_auth)):
        p = agent.get_profile(profile_id)
        if not p:
            raise HTTPException(404, "profile not found")
        return p.model_dump()

    @router.get("/profiles/{profile_id}/markdown")
    async def get_profile_md(profile_id: str, _: None = Depends(gen_auth)):
        p = agent.get_profile(profile_id)
        if not p:
            raise HTTPException(404, "profile not found")
        return {"id": p.id, "markdown": p.summary_markdown}

    @router.get("/packages")
    async def list_packages(_: None = Depends(gen_auth)):
        return {"items": agent.packages.list()}

    @router.get("/packages/{package_id}")
    async def get_package(package_id: str, _: None = Depends(gen_auth)):
        p = agent.packages.get(package_id)
        if not p:
            raise HTTPException(404, "package not found")
        return p

    @router.get("/hitl/pending")
    async def hitl_pending(_: None = Depends(gen_auth)):
        return {"items": [a.model_dump() for a in agent.hitl.list_pending()]}

    @router.post("/hitl/{hitl_id}/decide")
    async def hitl_decide(hitl_id: str, body: HitlDecision, _: None = Depends(admin)):
        if body.action == "approve":
            return agent.approve_hitl(hitl_id, decided_by=body.decided_by, note=body.note)
        if body.action == "reject":
            return agent.reject_hitl(hitl_id, decided_by=body.decided_by, note=body.note)
        raise HTTPException(400, "action must be approve or reject")

    @router.get("/keywords")
    async def keywords(_: None = Depends(gen_auth)):
        return {"items": [k.model_dump() for k in agent.keywords.list()], "summary": agent.keywords.summary()}

    @router.post("/keywords")
    async def keywords_upsert(body: KeywordUpsert, _: None = Depends(admin)):
        items = agent.keywords.upsert(body.keywords)
        return {"items": [k.model_dump() for k in items], "summary": agent.keywords.summary()}

    @router.get("/roi")
    async def roi(_: None = Depends(gen_auth)):
        return {"summary": agent.roi.summary(), "events": agent.roi.list_events()}

    @router.post("/roi")
    async def roi_record(body: RoiEvent, _: None = Depends(admin)):
        ev = agent.roi.record(
            hours_saved=body.hours_saved,
            leads_attributed=body.leads_attributed,
            revenue_usd=body.revenue_usd,
            note=body.note,
            run_id=body.run_id,
            profile_id=body.profile_id,
            source="manual",
        )
        return {"event": ev, "summary": agent.roi.summary()}

    @router.get("/brand")
    async def brand_get(_: None = Depends(gen_auth)):
        return {
            "voice_markdown": agent.brand.get_voice_markdown(),
            "meta": agent.brand.meta(),
        }

    @router.post("/brand")
    async def brand_save(body: BrandVoiceUpdate, _: None = Depends(admin)):
        return agent.brand.save_voice(body.voice_markdown, tone=body.tone, avoid=body.avoid)

    return router


def _run_response(run) -> dict:
    d = run.model_dump()
    # Trim huge module code from API responses
    mods = d.get("generated_modules") or {}
    slim = {}
    for k, v in mods.items():
        if isinstance(v, dict):
            slim[k] = {
                "id": v.get("id"),
                "path": v.get("path"),
                "exports": v.get("exports"),
                "code_chars": len(v.get("code") or ""),
            }
        else:
            slim[k] = v
    d["generated_modules"] = slim
    return d
