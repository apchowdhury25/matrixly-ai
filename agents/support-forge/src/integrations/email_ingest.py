"""Email ingest helpers — IMAP optional; webhook is primary production path."""

from __future__ import annotations

import email
import email.utils
import imaplib
from email.header import decode_header
from typing import Any


def decode_mime(value: str | None) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    out: list[str] = []
    for chunk, enc in parts:
        if isinstance(chunk, bytes):
            out.append(chunk.decode(enc or "utf-8", errors="replace"))
        else:
            out.append(chunk)
    return "".join(out)


def fetch_imap_unseen(cfg: dict, limit: int = 10) -> list[dict[str, Any]]:
    """
    Fetch unseen messages via IMAP when EMAIL_BACKEND=imap.
    Returns normalized payloads for the orchestrator.
    """
    em = cfg.get("email") or {}
    if (em.get("backend") or "none").lower() != "imap":
        return []
    host = em.get("imap_host") or ""
    user = em.get("imap_user") or ""
    password = em.get("imap_password") or ""
    port = int(em.get("imap_port") or 993)
    if not (host and user and password):
        return []

    results: list[dict[str, Any]] = []
    mail = imaplib.IMAP4_SSL(host, port)
    try:
        mail.login(user, password)
        mail.select("INBOX")
        typ, data = mail.search(None, "UNSEEN")
        if typ != "OK" or not data or not data[0]:
            return []
        ids = data[0].split()[-limit:]
        for mid in reversed(ids):
            typ, msg_data = mail.fetch(mid, "(RFC822)")
            if typ != "OK" or not msg_data or not msg_data[0]:
                continue
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)
            body = _extract_body(msg)
            results.append(
                {
                    "from_email": email.utils.parseaddr(msg.get("From", ""))[1],
                    "from_name": email.utils.parseaddr(msg.get("From", ""))[0],
                    "subject": decode_mime(msg.get("Subject")),
                    "body": body,
                    "message_id": msg.get("Message-ID"),
                }
            )
    finally:
        try:
            mail.logout()
        except Exception:
            pass
    return results


def _extract_body(msg: email.message.Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            disp = str(part.get("Content-Disposition") or "")
            if ctype == "text/plain" and "attachment" not in disp:
                payload = part.get_payload(decode=True) or b""
                charset = part.get_content_charset() or "utf-8"
                return payload.decode(charset, errors="replace")
        return ""
    payload = msg.get_payload(decode=True) or b""
    charset = msg.get_content_charset() or "utf-8"
    return payload.decode(charset, errors="replace")
