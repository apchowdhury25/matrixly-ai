"""Load config.yaml + environment for Starter Pack."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
STATIC = ROOT / "static"
AGENTS_ROOT = ROOT.parent  # agents/


def _ensure_dirs() -> None:
    for p in (DATA / "pack", DATA / "audit", DATA / "usage", DATA / "settings"):
        p.mkdir(parents=True, exist_ok=True)


def load_config() -> dict[str, Any]:
    load_dotenv(ROOT / ".env")
    _ensure_dirs()

    cfg_path = ROOT / "config.yaml"
    raw: dict[str, Any] = {}
    if cfg_path.exists():
        with cfg_path.open(encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

    business = raw.setdefault("business", {})
    if os.getenv("BUSINESS_NAME"):
        business["name"] = os.getenv("BUSINESS_NAME")
    if os.getenv("SUPPORT_EMAIL"):
        business["support_email"] = os.getenv("SUPPORT_EMAIL")
    if os.getenv("TIMEZONE"):
        business["timezone"] = os.getenv("TIMEZONE")

    raw["paths"] = {
        "root": str(ROOT),
        "data": str(DATA),
        "static": str(STATIC),
        "agents_root": str(AGENTS_ROOT),
    }
    raw["security"] = {
        "api_key": os.getenv("STARTER_API_KEY", "change-me-admin-key"),
        "widget_key": os.getenv("STARTER_WIDGET_KEY", "pk_live_change-me"),
    }
    raw["xai"] = {"api_key": os.getenv("XAI_API_KEY", "")}

    cors_env = os.getenv("CORS_ORIGINS")
    if cors_env:
        raw["cors_origins"] = [o.strip() for o in cors_env.split(",") if o.strip()]

    raw["agent_runtime"] = {
        "supportforge": {
            "url": os.getenv("SUPPORTFORGE_URL", "http://127.0.0.1:8787").rstrip("/"),
            "api_key": os.getenv("SUPPORTFORGE_API_KEY", "change-me-admin-key"),
            "enabled": os.getenv("SUPPORTFORGE_ENABLED", "true").lower()
            in {"1", "true", "yes"},
        },
        "bookwise": {
            "url": os.getenv("BOOKWISE_URL", "http://127.0.0.1:8790").rstrip("/"),
            "api_key": os.getenv("BOOKWISE_API_KEY", "change-me-admin-key"),
            "enabled": os.getenv("BOOKWISE_ENABLED", "true").lower()
            in {"1", "true", "yes"},
        },
        "invoiceforge": {
            "url": os.getenv("INVOICEFORGE_URL", "http://127.0.0.1:8791").rstrip("/"),
            "api_key": os.getenv("INVOICEFORGE_API_KEY", "change-me-admin-key"),
            "enabled": os.getenv("INVOICEFORGE_ENABLED", "true").lower()
            in {"1", "true", "yes"},
        },
        "local_data_fallback": os.getenv("LOCAL_DATA_FALLBACK", "true").lower()
        in {"1", "true", "yes"},
    }

    return raw
