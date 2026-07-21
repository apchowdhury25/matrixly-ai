"""Load Lead Qualifier configuration."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUTPUT_DIR = DATA_DIR / "output"
SF_DIR = OUTPUT_DIR / "salesforce"
ENRICHED_DIR = DATA_DIR / "leads" / "enriched"


def load_config(path: Path | None = None) -> dict[str, Any]:
    load_dotenv(ROOT / ".env")
    # Also load email-assistant secrets for optional Gmail ingest
    ea_env = ROOT / ".." / "email-assistant" / ".env"
    if ea_env.exists():
        load_dotenv(ea_env, override=False)

    cfg_path = path or (ROOT / "config.yaml")
    with open(cfg_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    xai = cfg.setdefault("xai", {})
    if os.getenv("XAI_API_KEY"):
        xai["api_key"] = os.getenv("XAI_API_KEY")
    xai["enabled"] = bool(xai.get("enabled", True)) and bool(
        xai.get("api_key") or os.getenv("XAI_API_KEY")
    )

    sf = cfg.setdefault("salesforce", {})
    if os.getenv("SALESFORCE_INSTANCE_URL"):
        sf["instance_url"] = os.getenv("SALESFORCE_INSTANCE_URL")
    if os.getenv("SALESFORCE_ACCESS_TOKEN"):
        sf["access_token"] = os.getenv("SALESFORCE_ACCESS_TOKEN")

    for d in (DATA_DIR, OUTPUT_DIR, SF_DIR, ENRICHED_DIR, DATA_DIR / "leads"):
        d.mkdir(parents=True, exist_ok=True)

    cfg["_paths"] = {
        "root": str(ROOT),
        "data": str(DATA_DIR),
        "sf_export": str(SF_DIR),
        "enriched": str(ENRICHED_DIR),
    }
    return cfg
