"""FastAPI application for Matrixly BookWise."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from .api.admin import build_admin_router
from .api.bookings import build_bookings_router
from .api.chat import build_chat_router
from .config import load_config
from .orchestrator import BookWise

cfg = load_config()
agent = BookWise(cfg)

app = FastAPI(
    title="Matrixly BookWise",
    description="Embeddable AI appointment booking agent for SMBs",
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

app.include_router(build_chat_router(agent, cfg))
app.include_router(build_admin_router(agent, cfg))
app.include_router(build_bookings_router(agent, cfg))

static_dir = Path(cfg["paths"]["static"])
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/v1/health")
def health():
    return {
        "ok": True,
        "service": "book-wise",
        "version": "1.0.0",
        "calendar": agent.calendar.backend,
        "upcoming": len(agent.bookings.list(upcoming_only=True, limit=50)),
    }


@app.get("/")
def root():
    return RedirectResponse(url="/static/admin/index.html")
