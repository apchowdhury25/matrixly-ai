"""Create the configured mail backend (IMAP or Gmail)."""

from __future__ import annotations

from typing import Any, Union

from .gmail_client import GmailClient
from .imap_client import ImapMailClient

MailClient = Union[ImapMailClient, GmailClient]


def create_mail_client(cfg: dict[str, Any]) -> MailClient:
    backend = ((cfg.get("agent") or {}).get("backend") or "imap").lower()
    if backend in {"imap", "thunderbird", "hostinger"}:
        return ImapMailClient(cfg)
    if backend in {"gmail", "google", "gmail_api"}:
        g = cfg["gmail"]
        return GmailClient(
            credentials_file=g["credentials_file"],
            token_file=g["token_file"],
            scopes=list(g.get("scopes") or []),
            user_id=g.get("user_id") or "me",
        )
    raise ValueError(f"Unknown mail backend: {backend!r} (use imap or gmail)")
