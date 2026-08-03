"""Load config.yaml + environment for ConnectForge."""

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
        DATA / "messages",
        DATA / "conversations",
        DATA / "hitl",
        DATA / "audit",
        DATA / "calls",
    ):
        p.mkdir(parents=True, exist_ok=True)
        keep = p / ".gitkeep"
        if not keep.exists():
            keep.write_text("", encoding="utf-8")


def _bool(val: str | None, default: bool = False) -> bool:
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


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

    twilio = raw.setdefault("twilio", {})
    twilio["account_sid"] = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    twilio["auth_token"] = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    twilio["phone_number"] = os.getenv("TWILIO_PHONE_NUMBER", "").strip()
    twilio["conversations_service_sid"] = os.getenv(
        "TWILIO_CONVERSATIONS_SERVICE_SID", ""
    ).strip() or twilio.get("conversations_service_sid") or ""
    if os.getenv("CONNECTFORGE_TEST_MODE") is not None:
        twilio["test_mode"] = _bool(os.getenv("CONNECTFORGE_TEST_MODE"), True)
    verified_env = os.getenv("TWILIO_VERIFIED_NUMBERS", "")
    verified = [n.strip() for n in verified_env.split(",") if n.strip()]
    if verified:
        twilio["verified_numbers"] = verified
    elif not twilio.get("verified_numbers"):
        twilio["verified_numbers"] = []

    hitl = raw.setdefault("hitl", {})
    if os.getenv("HITL_MODE"):
        hitl["mode"] = os.getenv("HITL_MODE")
    if os.getenv("HITL_REQUIRE_OUTBOUND") is not None:
        hitl["require_approval_outbound"] = _bool(
            os.getenv("HITL_REQUIRE_OUTBOUND"), True
        )
    hitl["auto_approve"] = _bool(os.getenv("HITL_AUTO_APPROVE"), False)

    xai = raw.setdefault("xai", {})
    xai["api_key"] = os.getenv("XAI_API_KEY") or xai.get("api_key")
    if os.getenv("XAI_MODEL"):
        xai["model"] = os.getenv("XAI_MODEL")
    if os.getenv("XAI_BASE_URL"):
        xai["base_url"] = os.getenv("XAI_BASE_URL")

    raw["public_base_url"] = (
        os.getenv("PUBLIC_BASE_URL") or ""
    ).rstrip("/") or f"http://localhost:{(raw.get('server') or {}).get('port', 8802)}"

    raw["paths"] = {
        "root": str(ROOT),
        "data": str(DATA),
        "prompts": str(PROMPTS),
        "static": str(STATIC),
        "brand": str(BRAND),
        "samples": str(SAMPLES),
    }
    raw["security"] = {
        "api_key": os.getenv("CONNECTFORGE_API_KEY", "change-me-admin-key"),
        "widget_key": os.getenv("CONNECTFORGE_WIDGET_KEY", "pk_live_change-me"),
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
