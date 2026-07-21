"""Load CRM Assistant configuration."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUTPUT = DATA / "output"
PENDING = DATA / "pending_writes"


def load_config(path: Path | None = None) -> dict[str, Any]:
    load_dotenv(ROOT / ".env")
    with open(path or ROOT / "config.yaml", encoding="utf-8") as f:
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

    store = (cfg.get("crm") or {}).get("store_path") or "data/crm_store.json"
    store_path = Path(store)
    if not store_path.is_absolute():
        store_path = ROOT / store_path

    for d in (DATA, OUTPUT, PENDING, OUTPUT / "salesforce", OUTPUT / "hubspot", DATA / "contacts", DATA / "activities"):
        d.mkdir(parents=True, exist_ok=True)

    cfg["_paths"] = {
        "root": str(ROOT),
        "store": str(store_path),
        "pending": str(PENDING),
        "output": str(OUTPUT),
    }
    return cfg
