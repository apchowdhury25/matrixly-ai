"""Watch uploads folder + optional IMAP for invoice attachments."""

from __future__ import annotations

import email
import email.utils
import imaplib
from email.header import decode_header
from pathlib import Path
from typing import Any


def list_upload_files(uploads_dir: str | Path) -> list[Path]:
    d = Path(uploads_dir)
    if not d.exists():
        return []
    files: list[Path] = []
    for p in sorted(d.iterdir()):
        if p.is_file() and p.suffix.lower() in {
            ".txt",
            ".md",
            ".csv",
            ".png",
            ".jpg",
            ".jpeg",
            ".webp",
            ".pdf",
            ".json",
        }:
            files.append(p)
    return files


def read_text_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def fetch_imap_invoice_bodies(cfg: dict, limit: int = 5) -> list[dict[str, Any]]:
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
            msg = email.message_from_bytes(msg_data[0][1])
            body = _extract_body(msg)
            subject = _decode_mime(msg.get("Subject"))
            results.append(
                {
                    "from_email": email.utils.parseaddr(msg.get("From", ""))[1],
                    "from_name": email.utils.parseaddr(msg.get("From", ""))[0],
                    "subject": subject,
                    "body": body,
                    "filename": f"email_{mid.decode() if isinstance(mid, bytes) else mid}.txt",
                }
            )
    finally:
        try:
            mail.logout()
        except Exception:
            pass
    return results


def _decode_mime(value: str | None) -> str:
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
