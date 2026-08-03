"""Load config.yaml + environment for SEO-Bespoke."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
PROMPTS = ROOT / "prompts"
STATIC = ROOT / "static"
BRAND = ROOT / "brand"
SAMPLES = ROOT / "samples"


def _ensure_dirs() -> None:
    for p in (
        DATA / "profiles",
        DATA / "packages",
        DATA / "hitl",
        DATA / "keywords",
        DATA / "roi",
        DATA / "sessions",
        DATA / "audit",
        DATA / "usage",
        DATA / "runs",
        DATA / "outputs",
    ):
        p.mkdir(parents=True, exist_ok=True)
        keep = p / ".gitkeep"
        if not keep.exists():
            keep.write_text("", encoding="utf-8")


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

    xai = raw.setdefault("xai", {})
    xai["api_key"] = os.getenv("XAI_API_KEY") or xai.get("api_key")
    if os.getenv("XAI_MODEL"):
        xai["model"] = os.getenv("XAI_MODEL")
    if os.getenv("XAI_BASE_URL"):
        xai["base_url"] = os.getenv("XAI_BASE_URL")

    hitl = raw.setdefault("hitl", {})
    if os.getenv("HITL_MODE"):
        hitl["mode"] = os.getenv("HITL_MODE")
    hitl["auto_approve"] = os.getenv("HITL_AUTO_APPROVE", "false").lower() in {
        "1",
        "true",
        "yes",
    }

    cost = raw.setdefault("cost", {})
    if os.getenv("COST_INPUT_PER_1M"):
        cost["input_per_1m_usd"] = float(os.getenv("COST_INPUT_PER_1M", "5"))
    if os.getenv("COST_OUTPUT_PER_1M"):
        cost["output_per_1m_usd"] = float(os.getenv("COST_OUTPUT_PER_1M", "15"))

    raw["paths"] = {
        "root": str(ROOT),
        "data": str(DATA),
        "prompts": str(PROMPTS),
        "static": str(STATIC),
        "brand": str(BRAND),
        "samples": str(SAMPLES),
        "profiles": str(DATA / "profiles"),
        "packages": str(DATA / "packages"),
        "outputs": str(DATA / "outputs"),
        "keywords": str(DATA / "keywords"),
        "roi": str(DATA / "roi"),
        "runs": str(DATA / "runs"),
    }
    raw["security"] = {
        "api_key": os.getenv("SEOBESPOKE_API_KEY", "change-me-admin-key"),
        "widget_key": os.getenv("SEOBESPOKE_WIDGET_KEY", "pk_live_change-me"),
    }

    cors_env = os.getenv("CORS_ORIGINS")
    if cors_env:
        raw["cors_origins"] = [o.strip() for o in cors_env.split(",") if o.strip()]

    return raw


def prompt_text(name: str) -> str:
    path = PROMPTS / f"{name}.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""
