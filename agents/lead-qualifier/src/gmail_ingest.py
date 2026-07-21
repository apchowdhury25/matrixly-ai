"""Optional: pull lead-like inbound emails from Gmail via Email Assistant stack."""

from __future__ import annotations

import re
import sys
from email.utils import parseaddr
from pathlib import Path
from typing import Any

from .models import Lead


def _email_assistant_root(cfg: dict[str, Any]) -> Path:
    root = Path((cfg.get("_paths") or {}).get("root") or ".")
    rel = (cfg.get("gmail") or {}).get("email_assistant_env") or "../email-assistant/.env"
    env_path = (root / rel).resolve()
    return env_path.parent


def ingest_leads_from_gmail(cfg: dict[str, Any], *, max_messages: int | None = None) -> list[Lead]:
    """Best-effort Gmail ingest. Returns [] if email-assistant / credentials unavailable."""
    gmail_cfg = cfg.get("gmail") or {}
    if not gmail_cfg.get("enabled", True):
        return []

    ea_root = _email_assistant_root(cfg)
    if not ea_root.exists():
        print(f"warn: email-assistant not found at {ea_root}")
        return []

    # Import Imap client from sibling agent
    sys.path.insert(0, str(ea_root))
    try:
        from src.config import load_config as load_mail_config  # type: ignore
        from src.imap_client import ImapMailClient  # type: ignore
    except Exception as exc:  # noqa: BLE001
        print(f"warn: cannot import email-assistant client: {exc}")
        return []

    import os

    os.environ.setdefault("EMAIL_PROFILE", gmail_cfg.get("profile") or "gmail")
    try:
        mail_cfg = load_mail_config()
        # Force gmail profile values
        mail_cfg.setdefault("agent", {})["profile"] = gmail_cfg.get("profile") or "gmail"
        client = ImapMailClient(mail_cfg)
        client.authenticate()
    except Exception as exc:  # noqa: BLE001
        print(f"warn: Gmail connect failed: {exc}")
        return []

    max_n = max_messages or int(gmail_cfg.get("max_messages") or 30)
    keywords = [k.lower() for k in gmail_cfg.get("lead_subject_keywords") or []]
    messages = client.fetch_inbox(max_results=max_n, unread_only=False)

    leads: list[Lead] = []
    for msg in messages:
        subj = (msg.subject or "").lower()
        body = (msg.body or msg.snippet or "").lower()
        blob = f"{subj} {body}"
        if keywords and not any(k in blob for k in keywords):
            continue
        # Prefer reply-to external senders as leads
        name, email = parseaddr(msg.from_raw or "")
        email = (email or msg.from_email or "").lower()
        if not email or email.endswith("@matrixbazaar.com"):
            continue
        if email.endswith("@gmail.com") and "noreply" in email:
            continue

        first, last = "", ""
        if name:
            parts = name.split(None, 1)
            first = parts[0]
            last = parts[1] if len(parts) > 1 else ""

        leads.append(
            Lead(
                email=email,
                first_name=first,
                last_name=last,
                full_name=name or email,
                company="",
                title="",
                source="Gmail inbound",
                notes=f"Subject: {msg.subject}\n\n{(msg.snippet or msg.body or '')[:800]}",
                raw={"gmail_id": msg.id, "subject": msg.subject},
            )
        )
    return leads
