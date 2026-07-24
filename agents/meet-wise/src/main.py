"""FastAPI app for Matrixly MeetWise."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from .api.admin import build_admin_router
from .api.meetings import build_meetings_router
from .config import load_config
from .orchestrator import MeetWise

cfg = load_config()
agent = MeetWise(cfg)

app = FastAPI(
    title="Matrixly MeetWise",
    description="Meeting capture, summaries, actions, CRM, recap emails",
    version="1.0.0",
)

origins = cfg.get("cors_origins") or ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(build_meetings_router(agent, cfg))
app.include_router(build_admin_router(agent, cfg))

static_dir = Path(cfg["paths"]["static"])
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/v1/health")
def health():
    st = agent.status()
    return {
        "ok": True,
        "service": "meet-wise",
        "version": "1.0.0",
        "meetings": st.get("meetings"),
        "pending_review": st.get("pending_review"),
    }


@app.get("/")
def root():
    return RedirectResponse(url="/static/dashboard/index.html")
