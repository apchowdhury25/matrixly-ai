"""Load Shipping Assistant config."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUTPUT = DATA / "output"


def load_config(path: Path | None = None) -> dict[str, Any]:
    load_dotenv(ROOT / ".env")
    with open(path or ROOT / "config.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    ss = cfg.setdefault("shipstation", {})
    ss["api_key"] = os.getenv("SHIPSTATION_API_KEY") or ss.get("api_key") or ""
    ss["api_secret"] = os.getenv("SHIPSTATION_API_SECRET") or ss.get("api_secret") or ""
    mode = (os.getenv("SHIPSTATION_MODE") or ss.get("mode") or "auto").lower()
    if mode == "auto":
        mode = "live" if (ss["api_key"] and ss["api_secret"]) else "demo"
    ss["mode"] = mode

    xai = cfg.setdefault("xai", {})
    if os.getenv("XAI_API_KEY"):
        xai["api_key"] = os.getenv("XAI_API_KEY")
    xai["enabled"] = bool(xai.get("enabled", True)) and bool(
        xai.get("api_key") or os.getenv("XAI_API_KEY")
    )

    for d in (DATA, OUTPUT, DATA / "orders"):
        d.mkdir(parents=True, exist_ok=True)

    cfg["_paths"] = {"root": str(ROOT), "data": str(DATA), "output": str(OUTPUT)}
    return cfg
