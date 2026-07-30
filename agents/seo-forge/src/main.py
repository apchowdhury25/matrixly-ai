"""FastAPI app for Matrixly SEOForge."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from .api.admin import build_admin_router
from .api.seo import build_seo_router
from .config import load_config
from .orchestrator import SEOForge

cfg = load_config()
agent = SEOForge(cfg)

app = FastAPI(
    title="Matrixly SEOForge",
    description="SEO & brand marketing agent for US SMBs — research, content, local SEO, HITL, ROI",
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

app.include_router(build_seo_router(agent, cfg))
app.include_router(build_admin_router(agent, cfg))

static_dir = Path(cfg["paths"]["static"])
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/v1/health")
def health():
    st = agent.status()
    return {
        "ok": True,
        "service": "seo-forge",
        "version": "1.0.0",
        "jobs": st.get("jobs"),
        "pending_review": st.get("pending_review"),
        "keywords": st.get("keywords"),
        "roi": st.get("roi"),
    }


@app.get("/")
def root():
    return RedirectResponse(url="/static/dashboard/index.html")
