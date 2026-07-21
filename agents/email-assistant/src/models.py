"""Shared email models for IMAP and Gmail backends."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EmailMessage:
    id: str
    thread_id: str
    subject: str
    from_raw: str
    from_email: str
    from_name: str
    to: str
    date: str
    snippet: str
    body: str
    label_ids: list[str] = field(default_factory=list)
    is_unread: bool = False
    message_id_header: str = ""
    uid: str = ""
    folder: str = "INBOX"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "thread_id": self.thread_id,
            "subject": self.subject,
            "from": self.from_raw,
            "from_email": self.from_email,
            "from_name": self.from_name,
            "to": self.to,
            "date": self.date,
            "snippet": self.snippet,
            "body": self.body[:4000],
            "label_ids": self.label_ids,
            "is_unread": self.is_unread,
            "folder": self.folder,
            "uid": self.uid,
        }
