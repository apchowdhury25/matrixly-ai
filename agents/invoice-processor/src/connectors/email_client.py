"""Email client abstraction — Stub today, Gmail later."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol


@dataclass
class EmailMessage:
    message_id: str
    subject: str
    from_address: str
    body_text: str
    attachment_paths: list[str]


class EmailClient(Protocol):
    async def fetch_message(self, message_id: str) -> EmailMessage: ...

    async def extract_invoice_payload(self, message_id: str) -> str:
        """Return best text representation of invoice from body/attachments."""
        ...


class StubEmailClient:
    """In-memory / path-based email stub for demos and tests."""

    def __init__(self) -> None:
        self._messages: dict[str, EmailMessage] = {}

    def seed(self, msg: EmailMessage) -> None:
        self._messages[msg.message_id] = msg

    async def fetch_message(self, message_id: str) -> EmailMessage:
        if message_id not in self._messages:
            raise KeyError(f"Email message not found: {message_id}")
        return self._messages[message_id]

    async def extract_invoice_payload(self, message_id: str) -> str:
        msg = await self.fetch_message(message_id)
        parts = [f"Subject: {msg.subject}", f"From: {msg.from_address}", "", msg.body_text]
        # Attachment paths would be PDF-extracted by the pipeline
        if msg.attachment_paths:
            parts.append("\nAttachments: " + ", ".join(msg.attachment_paths))
        return "\n".join(parts)
