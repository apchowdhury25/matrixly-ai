"""FastAPI app for Matrixly ContentForge."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from .api.admin import build_admin_router
from .api.content import build_content_router
from .config import load_config
from .orchestrator import ContentForge

cfg = load_config()
agent = ContentForge(cfg)

app = FastAPI(
    title="Matrixly ContentForge",
    description="Content creation & repurposing agent for SMBs",
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

app.include_router(build_content_router(agent, cfg))
app.include_router(build_admin_router(agent, cfg))

static_dir = Path(cfg["paths"]["static"])
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/v1/health")
def health():
    st = agent.status()
    return {
        "ok": True,
        "service": "content-forge",
        "version": "1.0.0",
        "jobs": st.get("jobs"),
        "pending_review": st.get("pending_review"),
    }


@app.get("/")
def root():
    return RedirectResponse(url="/static/workspace/index.html")
