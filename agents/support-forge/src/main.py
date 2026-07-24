"""FastAPI application entrypoint for Matrixly SupportForge."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from .api.admin import build_admin_router
from .api.chat import build_chat_router
from .api.kb import build_kb_router
from .api.webhooks import build_webhook_router
from .config import load_config
from .orchestrator import SupportForge

cfg = load_config()
forge = SupportForge(cfg)

app = FastAPI(
    title="Matrixly SupportForge",
    description="Embeddable AI customer support agent for SMBs",
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

app.include_router(build_chat_router(forge, cfg))
app.include_router(build_admin_router(forge, cfg))
app.include_router(build_webhook_router(forge, cfg))
app.include_router(build_kb_router(forge, cfg))

static_dir = Path(cfg["paths"]["static"])
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/v1/health")
def health():
    return {
        "ok": True,
        "service": "support-forge",
        "version": "1.0.0",
        "kb_docs": forge.vectors.stats().get("documents", 0),
    }


@app.get("/")
def root():
    return RedirectResponse(url="/static/admin/index.html")


@app.on_event("startup")
def on_startup():
    # Auto-seed if index empty
    if forge.vectors.stats().get("documents", 0) == 0:
        forge.seed_knowledge()
