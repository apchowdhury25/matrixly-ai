"""FastAPI app — Matrixly ETF Portfolio Analyzer."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from .api.admin import build_admin_router
from .api.analyze import build_analyze_router
from .config import load_config
from .orchestrator import ETFAnalyzer

cfg = load_config()
agent = ETFAnalyzer(cfg)

app = FastAPI(
    title="Matrixly ETF Portfolio Analyzer",
    description="Live ETF analysis — yield, NAV risk, tax-aware notes, optional Notion save",
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

app.include_router(build_analyze_router(agent, cfg))
app.include_router(build_admin_router(agent, cfg))

static_dir = Path(cfg["paths"]["static"])
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/v1/health")
def health():
    st = agent.status()
    return {
        "ok": True,
        "service": "etf-analyzer",
        "version": "1.0.0",
        "default_ticker": st.get("default_ticker"),
        "reports": st.get("reports"),
        "notion_enabled": st.get("notion_enabled"),
    }


@app.get("/")
def root():
    return RedirectResponse(url="/static/dashboard/index.html")
