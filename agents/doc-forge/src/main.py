"""FastAPI app for Matrixly DocForge."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from .api.admin import build_admin_router
from .api.docs import build_docs_router
from .config import load_config
from .orchestrator import DocForge

cfg = load_config()
agent = DocForge(cfg)

app = FastAPI(
    title="Matrixly DocForge",
    description="Professional business documents — proposals, quotes, contracts, reports",
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

app.include_router(build_docs_router(agent, cfg))
app.include_router(build_admin_router(agent, cfg))

static_dir = Path(cfg["paths"]["static"])
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/v1/health")
def health():
    st = agent.status()
    return {
        "ok": True,
        "service": "doc-forge",
        "version": "1.0.0",
        "documents": st.get("documents"),
        "pending_approval": st.get("pending_approval"),
        "templates": st.get("templates"),
    }


@app.get("/")
def root():
    return RedirectResponse(url="/static/workspace/index.html")
