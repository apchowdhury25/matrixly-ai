"""FastAPI app — Matrixly Starter Pack dashboard gateway."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from .api.admin import build_admin_router
from .api.pack import build_pack_router
from .config import load_config
from .pack import StarterPack

cfg = load_config()
pack = StarterPack(cfg)

app = FastAPI(
    title="Matrixly Starter Pack",
    description="Unified dashboard for SupportForge, BookWise, and InvoiceForge",
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

app.include_router(build_pack_router(pack, cfg))
app.include_router(build_admin_router(pack, cfg))

static_dir = Path(cfg["paths"]["static"])
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/v1/health")
def health():
    st = pack.status()
    return {
        "ok": True,
        "service": "starter-pack",
        "version": "1.0.0",
        "agents_online": st.get("agents_online"),
        "agents_enabled": st.get("agents_enabled"),
        "pending_hitl": st.get("pending_hitl"),
    }


@app.get("/")
def root():
    return RedirectResponse(url="/static/dashboard/index.html")
