"""Create the configured mail backend (IMAP, Gmail API, or Test Mode)."""

from __future__ import annotations

from typing import Any, Union

from .gmail_client import DEFAULT_SCOPES, GmailClient
from .imap_client import ImapMailClient
from .test_mode import TestMailClient

MailClient = Union[ImapMailClient, GmailClient, TestMailClient]


def create_mail_client(cfg: dict[str, Any], *, force_test: bool = False) -> MailClient:
    backend = ((cfg.get("agent") or {}).get("backend") or "imap").lower()
    if force_test or backend in {"test", "demo", "sample", "test_mode"}:
        return TestMailClient(cfg)
    if backend in {"imap", "thunderbird", "hostinger"}:
        return ImapMailClient(cfg)
    if backend in {"gmail", "google", "gmail_api"}:
        g = cfg.get("gmail") or {}
        scopes = list(g.get("scopes") or DEFAULT_SCOPES)
        return GmailClient(
            credentials_file=g["credentials_file"],
            token_file=g["token_file"],
            scopes=scopes,
            user_id=g.get("user_id") or "me",
        )
    raise ValueError(
        f"Unknown mail backend: {backend!r}. Use: gmail | imap | test"
    )
