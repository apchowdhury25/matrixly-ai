"""Analyze + chat API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from ..models import AnalyzeRequest, ChatRequest
from ..orchestrator import ETFAnalyzer
from .deps import rate_limiter, require_api_key, require_widget_or_api_key


def build_analyze_router(agent: ETFAnalyzer, cfg: dict) -> APIRouter:
    router = APIRouter(prefix="/v1", tags=["etf"])
    admin = require_api_key(cfg)
    widget = require_widget_or_api_key(cfg)
    limit = int((cfg.get("rate_limit") or {}).get("analyze_per_minute") or 30)

    @router.post("/analyze")
    async def analyze(body: AnalyzeRequest, request: Request, _: None = Depends(widget)):
        rate_limiter.check(f"etf:{request.client.host if request.client else 'x'}", limit)
        report = agent.analyze(body.ticker, save_to_notion=body.save_to_notion)
        return report.model_dump()

    @router.post("/chat")
    async def chat(body: ChatRequest, request: Request, _: None = Depends(widget)):
        rate_limiter.check(f"etfchat:{request.client.host if request.client else 'x'}", limit)
        return agent.chat(body.message, body.session_id, save_to_notion=body.save_to_notion).model_dump()

    @router.get("/reports")
    async def reports(_: None = Depends(admin)):
        return {"items": [r.model_dump() for r in agent.store.list()]}

    @router.get("/reports/{report_id}")
    async def get_report(report_id: str, _: None = Depends(admin)):
        r = agent.store.get(report_id)
        if not r:
            raise HTTPException(404, "Report not found")
        return r.model_dump()

    @router.post("/reports/{report_id}/notion")
    async def save_notion(report_id: str, _: None = Depends(admin)):
        r = agent.store.get(report_id)
        if not r:
            raise HTTPException(404, "Report not found")
        result = agent.notion.save(r)
        if result.get("page_id"):
            r.notion_page_id = result.get("page_id")
            r.notion_url = result.get("url")
            agent.store.save(r)
        return {"report": r.model_dump(), "notion": result}

    return router
