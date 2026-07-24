"""Load config.yaml + environment variables."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
KNOWLEDGE = ROOT / "knowledge"
PROMPTS = ROOT / "prompts"
STATIC = ROOT / "static"


def _ensure_dirs() -> None:
    for p in (
        DATA / "tickets",
        DATA / "sessions",
        DATA / "audit",
        DATA / "usage",
        DATA / "vector",
        DATA / "hitl",
        DATA / "followups",
        DATA / "crm",
    ):
        p.mkdir(parents=True, exist_ok=True)


def load_config() -> dict[str, Any]:
    load_dotenv(ROOT / ".env")
    _ensure_dirs()

    cfg_path = ROOT / "config.yaml"
    raw: dict[str, Any] = {}
    if cfg_path.exists():
        with cfg_path.open(encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

    # Env overrides
    business = raw.setdefault("business", {})
    if os.getenv("BUSINESS_NAME"):
        business["name"] = os.getenv("BUSINESS_NAME")
    if os.getenv("SUPPORT_EMAIL"):
        business["support_email"] = os.getenv("SUPPORT_EMAIL")
    if os.getenv("TIMEZONE"):
        business["timezone"] = os.getenv("TIMEZONE")

    xai = raw.setdefault("xai", {})
    xai["api_key"] = os.getenv("XAI_API_KEY") or xai.get("api_key")
    if os.getenv("XAI_MODEL"):
        xai["model"] = os.getenv("XAI_MODEL")
    if os.getenv("XAI_BASE_URL"):
        xai["base_url"] = os.getenv("XAI_BASE_URL")

    hitl = raw.setdefault("hitl", {})
    if os.getenv("HITL_MODE"):
        hitl["mode"] = os.getenv("HITL_MODE")
    hitl["auto_approve"] = (
        os.getenv("HITL_AUTO_APPROVE", "false").lower() in {"1", "true", "yes"}
    )

    cost = raw.setdefault("cost", {})
    if os.getenv("COST_INPUT_PER_1M"):
        cost["input_per_1m_usd"] = float(os.getenv("COST_INPUT_PER_1M", "5"))
    if os.getenv("COST_OUTPUT_PER_1M"):
        cost["output_per_1m_usd"] = float(os.getenv("COST_OUTPUT_PER_1M", "15"))

    raw["paths"] = {
        "root": str(ROOT),
        "data": str(DATA),
        "knowledge": str(KNOWLEDGE),
        "prompts": str(PROMPTS),
        "static": str(STATIC),
    }

    raw["security"] = {
        "api_key": os.getenv("SUPPORTFORGE_API_KEY", "change-me-admin-key"),
        "widget_key": os.getenv("SUPPORTFORGE_WIDGET_KEY", "pk_live_change-me"),
    }

    cors_env = os.getenv("CORS_ORIGINS")
    if cors_env:
        raw["cors_origins"] = [o.strip() for o in cors_env.split(",") if o.strip()]

    # Optional integrations
    raw["email"] = {
        "backend": os.getenv("EMAIL_BACKEND", "none"),
        "imap_host": os.getenv("EMAIL_IMAP_HOST", ""),
        "imap_port": int(os.getenv("EMAIL_IMAP_PORT", "993") or "993"),
        "imap_user": os.getenv("EMAIL_IMAP_USER", ""),
        "imap_password": os.getenv("EMAIL_IMAP_PASSWORD", ""),
    }
    raw["notion"] = {
        "api_key": os.getenv("NOTION_API_KEY", ""),
        "database_id": os.getenv("NOTION_DATABASE_ID", ""),
    }
    raw["zendesk"] = {
        "subdomain": os.getenv("ZENDESK_SUBDOMAIN", ""),
        "email": os.getenv("ZENDESK_EMAIL", ""),
        "api_token": os.getenv("ZENDESK_API_TOKEN", ""),
    }

    return raw


def prompt_text(name: str) -> str:
    path = PROMPTS / f"{name}.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""
