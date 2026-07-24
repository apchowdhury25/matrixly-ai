"""Shared QA configuration."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

# Public marketing pages (clean folder paths after npm run build)
PUBLIC_PAGES = [
    "",  # home → /
    "agents",
    "products",
    "integrations",
    "pricing",
    "lead-qualifier",
    "email-assistant",
    "crm-assistant",
    "shipping-assistant",
    "shipping-assistant-guide",
    "support-forge",
    "book-wise",
    "invoice-forge",
    "content-forge",
    "meet-wise",
]

# Authorized developer page (passphrase gated; linked from footer)
DEV_PAGES = [
    "admin",
]


def base_url() -> str:
    return (os.getenv("BASE_URL") or "http://127.0.0.1:8080").rstrip("/")


def url_for(page: str) -> str:
    page = page.lstrip("/")
    if not page:
        return base_url() + "/"
    return f"{base_url()}/{page}"


def headless() -> bool:
    return os.getenv("SELENIUM_HEADLESS", "true").lower() in {"1", "true", "yes"}


def playwright_headless() -> bool:
    return os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() in {"1", "true", "yes"}


def timeout_ms() -> int:
    return int(os.getenv("DEFAULT_TIMEOUT_MS", "15000"))


def selenium_browser() -> str:
    return (os.getenv("SELENIUM_BROWSER") or "chrome").lower()
