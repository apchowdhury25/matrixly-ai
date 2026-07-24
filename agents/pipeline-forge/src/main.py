"""FastAPI app for Matrixly PipelineForge."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from .api.admin import build_admin_router
from .api.pipeline import build_pipeline_router
from .config import load_config
from .orchestrator import PipelineForge

cfg = load_config()
agent = PipelineForge(cfg)

app = FastAPI(
    title="Matrixly PipelineForge",
    description="Pipeline scoring, prioritization, risk, CRM updates for SMBs",
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

app.include_router(build_pipeline_router(agent, cfg))
app.include_router(build_admin_router(agent, cfg))

static_dir = Path(cfg["paths"]["static"])
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/v1/health")
def health():
    st = agent.status()
    return {
        "ok": True,
        "service": "pipeline-forge",
        "version": "1.0.0",
        "runs": st.get("runs"),
        "pending_review": st.get("pending_review"),
        "latest_health": st.get("latest_health"),
    }


@app.get("/")
def root():
    return RedirectResponse(url="/static/dashboard/index.html")
