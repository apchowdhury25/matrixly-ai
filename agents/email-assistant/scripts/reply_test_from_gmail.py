#!/usr/bin/env python3
"""
Reply from usmatrixbazaar@gmail.com to the Matrixly work->Gmail test thread.

Requires in .env:
  EMAIL_PROFILE=gmail
  EMAIL_GMAIL_USER=usmatrixbazaar@gmail.com
  EMAIL_GMAIL_PASSWORD=<Google App Password>
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from email.message import EmailMessage as MimeEmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path

import smtplib
import ssl

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ["EMAIL_PROFILE"] = "gmail"

from src.config import load_config
from src.imap_client import ImapMailClient


def main() -> int:
    cfg = load_config()
    client = ImapMailClient(cfg)
    client.authenticate()
    profile = client.profile()
    print(f"Connected Gmail: {profile.get('emailAddress')} ({profile.get('messagesTotal')} inbox)")

    # Find the test message from work mailbox
    candidates = client.fetch_inbox(max_results=50, unread_only=False)
    # Also try UNSEEN first batch already covered; search broader
    if len(candidates) < 50:
        refs = client.list_messages(query="in:inbox", max_results=80)
        seen = {m.id for m in candidates}
        for r in refs:
            if r["id"] in seen:
                continue
            try:
                candidates.append(client.get_message(r["id"]))
            except Exception:
                pass

    target = None
    for m in candidates:
        subj = (m.subject or "").lower()
        frm = (m.from_email or "").lower()
        if "anwar.chowdhury@matrixbazaar.com" in frm and (
            "matrixly test" in subj or "work -> gmail" in subj or "work → gmail" in subj
        ):
            target = m
            break
    if target is None:
        for m in candidates:
            if "anwar.chowdhury@matrixbazaar.com" in (m.from_email or "").lower():
                if "test" in (m.subject or "").lower() or "matrixly" in (m.subject or "").lower():
                    target = m
                    break

    if target is None:
        print("ERROR: Could not find the work->Gmail test email in Gmail inbox.")
        print("Recent subjects:")
        for m in candidates[:15]:
            print(f"  - {m.from_email} | {m.subject}")
        return 1

    print(f"Replying to: {target.subject!r} from {target.from_email} id={target.id}")

    now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    body = (
        "Hello Anwar,\n\n"
        "This is a test reply from my Gmail mailbox (usmatrixbazaar@gmail.com) "
        "to the Matrixly Email Assistant test message.\n\n"
        f"Sent: {now}\n\n"
        "—\n"
        "Anwar Pasha Chowdhury\n"
        "usmatrixbazaar@gmail.com\n"
    )

    subject = target.subject or "Matrixly Test"
    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"

    mime = MimeEmailMessage()
    mime["From"] = client.email_address
    mime["To"] = "anwar.chowdhury@matrixbazaar.com"
    mime["Subject"] = subject
    mime["Date"] = formatdate(localtime=True)
    mime["Message-ID"] = make_msgid(domain="gmail.com")
    if target.message_id_header:
        mime["In-Reply-To"] = target.message_id_header
        mime["References"] = target.message_id_header
    mime.set_content(body)

    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL(client.smtp_host, client.smtp_port, context=ctx) as smtp:
        smtp.login(client.email_address, client.password)
        smtp.send_message(mime)

    # Best-effort Sent copy
    try:
        sent = client._ensure_folder(client.sent_folder)
        client.conn.append(sent, None, None, mime.as_bytes())
        print(f"Copied to Sent: {sent}")
    except Exception as exc:  # noqa: BLE001
        print(f"Sent folder note: {exc}")

    print("SENT OK (Gmail reply)")
    print(f"  from: {client.email_address}")
    print(f"  to:   anwar.chowdhury@matrixbazaar.com")
    print(f"  subj: {subject}")
    print(f"  id:   {mime['Message-ID']}")
    print("--- body ---")
    print(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
