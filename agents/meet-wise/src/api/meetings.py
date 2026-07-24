"""Meeting process / upload API."""

from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile

from ..models import ProcessRequest
from ..orchestrator import MeetWise
from .deps import rate_limiter, require_api_key, require_widget_or_api_key


def build_meetings_router(agent: MeetWise, cfg: dict) -> APIRouter:
    router = APIRouter(prefix="/v1", tags=["meetings"])
    admin = require_api_key(cfg)
    proc = require_widget_or_api_key(cfg)
    limit = int((cfg.get("rate_limit") or {}).get("process_per_minute") or 20)

    @router.post("/process")
    async def process(
        body: ProcessRequest,
        request: Request,
        _: None = Depends(proc),
    ):
        rate_limiter.check(f"mtg:{request.client.host if request.client else 'x'}", limit)
        if not body.transcript.strip():
            raise HTTPException(400, "transcript required")
        m = agent.process(
            body.transcript,
            title=body.title,
            platform=body.platform,
            meeting_date=body.meeting_date,
            participants=body.participants,
            metadata=body.metadata,
        )
        return m.model_dump()

    @router.post("/upload")
    async def upload(
        request: Request,
        file: UploadFile = File(...),
        title: str = Form(""),
        _: None = Depends(proc),
    ):
        rate_limiter.check(f"mtg:{request.client.host if request.client else 'x'}", limit)
        uploads = Path(cfg["paths"]["uploads"])
        uploads.mkdir(parents=True, exist_ok=True)
        safe = Path(file.filename or "transcript.txt").name
        dest = uploads / safe
        i = 0
        while dest.exists():
            i += 1
            dest = uploads / f"{Path(safe).stem}_{i}{Path(safe).suffix}"
        with dest.open("wb") as f:
            shutil.copyfileobj(file.file, f)
        m = agent.process_file(dest)
        if title:
            m.title = title
            agent.store.save(m)
        return m.model_dump()

    @router.get("/meetings")
    async def list_meetings(status: str | None = None, _: None = Depends(admin)):
        return {"items": [m.model_dump() for m in agent.store.list(status=status)]}

    @router.get("/meetings/{meeting_id}")
    async def get_meeting(meeting_id: str, _: None = Depends(admin)):
        m = agent.store.get(meeting_id)
        if not m:
            raise HTTPException(404, "Meeting not found")
        return m.model_dump()

    return router
