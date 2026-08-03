"""FastAPI app for Matrixly SEO-Bespoke."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from .api.admin import build_admin_router
from .api.bespoke import build_bespoke_router
from .config import load_config
from .orchestrator import SEOBespoke

cfg = load_config()
agent = SEOBespoke(cfg)

app = FastAPI(
    title="Matrixly SEO-Bespoke",
    description=(
        "Custom SEO agent factory — interactive quiz → Business SEO Profile → "
        "specialized Python agent package (parallel 20-node graph)"
    ),
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

app.include_router(build_bespoke_router(agent, cfg))
app.include_router(build_admin_router(agent, cfg))

static_dir = Path(cfg["paths"]["static"])
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/v1/health")
def health():
    st = agent.status()
    return {
        "ok": True,
        "service": "seo-bespoke",
        "version": "1.0.0",
        "runs": st.get("runs"),
        "profiles": st.get("profiles"),
        "packages": st.get("packages"),
        "pending_review": st.get("pending_review"),
        "graph_nodes": (st.get("graph") or {}).get("nodes"),
        "keywords": st.get("keywords"),
        "roi": st.get("roi"),
    }


@app.get("/")
def root():
    return RedirectResponse(url="/static/dashboard/index.html")
