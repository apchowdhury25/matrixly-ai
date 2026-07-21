#!/usr/bin/env python3
"""Create draft reply to Gonzalo 'Test Email' thread."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.agent import EmailAssistant
from src.config import load_config


def main() -> int:
    cfg = load_config()
    agent = EmailAssistant(cfg)
    agent.connect()
    client = agent.client

    msgs = client.fetch_inbox(max_results=100, unread_only=False)
    hits = [m for m in msgs if "test email" in (m.subject or "").lower()]
    if not hits:
        refs = client.list_messages(query="in:inbox", max_results=150)
        for r in refs:
            m = client.get_message(r["id"])
            if "test email" in (m.subject or "").lower():
                hits.append(m)

    if not hits:
        print("ERROR: No message with subject 'Test Email'")
        return 1

    target = next(
        (
            m
            for m in hits
            if "gonzalo" in (m.from_email or "").lower()
            or "gonzalo" in (m.from_raw or "").lower()
        ),
        hits[0],
    )

    sig = ((cfg.get("draft") or {}).get("signature") or "").strip()
    body = "Hello Gonzalo, I received your email"
    if sig:
        body = f"{body}\n\n{sig}"

    created = client.create_draft_reply(target, body)
    print("Draft created (not sent)")
    print(f"  to:        {target.from_email}")
    print(f"  subject:   {created.get('message', {}).get('subject') or target.subject}")
    print(f"  reply_to:  {target.id}")
    print(f"  draft_id:  {created.get('id')}")
    print(f"  folder:    {created.get('folder')}")
    print("--- body ---")
    print(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
