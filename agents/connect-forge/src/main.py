"""FastAPI app for Matrixly ConnectForge (Twilio SMS & Voice)."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from .api.connect import build_connect_router
from .config import load_config
from .orchestrator import ConnectForge

cfg = load_config()
agent = ConnectForge(cfg)

app = FastAPI(
    title="Matrixly ConnectForge",
    description="Twilio SMS & simple voice agent for Houston SMBs — HITL outbound, Conversations, test mode",
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

app.include_router(build_connect_router(agent, cfg))

static_dir = Path(cfg["paths"]["static"])
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/v1/health")
def health():
    st = agent.status()
    conn = st.get("connection") or {}
    return {
        "ok": True,
        "service": "connect-forge",
        "version": "1.0.0",
        "connection_status": conn.get("status"),
        "test_mode": conn.get("test_mode"),
        "messages": st.get("messages"),
        "pending_hitl": st.get("pending_hitl"),
        "market": st.get("market"),
    }


@app.get("/")
def root():
    return RedirectResponse(url="/static/dashboard/index.html")
