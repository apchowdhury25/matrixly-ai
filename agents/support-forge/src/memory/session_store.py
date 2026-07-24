"""JSON session memory for chat conversations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..models import ChatMessage, Customer, new_id, utc_now


class SessionStore:
    def __init__(self, data_dir: str | Path) -> None:
        self.dir = Path(data_dir) / "sessions"
        self.dir.mkdir(parents=True, exist_ok=True)

    def _path(self, session_id: str) -> Path:
        return self.dir / f"{session_id}.json"

    def create(
        self,
        customer: Customer | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        sid = new_id("ses_")
        doc = {
            "session_id": sid,
            "customer": (customer or Customer()).model_dump(),
            "messages": [],
            "metadata": metadata or {},
            "created_at": utc_now(),
            "updated_at": utc_now(),
        }
        self._write(sid, doc)
        return doc

    def get(self, session_id: str) -> dict[str, Any] | None:
        p = self._path(session_id)
        if not p.exists():
            return None
        with p.open(encoding="utf-8") as f:
            return json.load(f)

    def get_or_create(
        self,
        session_id: str | None,
        customer: Customer | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if session_id:
            existing = self.get(session_id)
            if existing:
                if customer:
                    c = existing.get("customer") or {}
                    for k, v in customer.model_dump(exclude_none=True).items():
                        if v:
                            c[k] = v
                    existing["customer"] = c
                    self._write(session_id, existing)
                return existing
        return self.create(customer=customer, metadata=metadata)

    def append_messages(self, session_id: str, messages: list[ChatMessage]) -> dict[str, Any]:
        doc = self.get(session_id)
        if not doc:
            doc = self.create()
            session_id = doc["session_id"]
        for m in messages:
            doc["messages"].append(m.model_dump())
        doc["updated_at"] = utc_now()
        self._write(session_id, doc)
        return doc

    def history(self, session_id: str, limit: int = 20) -> list[ChatMessage]:
        doc = self.get(session_id)
        if not doc:
            return []
        msgs = doc.get("messages") or []
        return [ChatMessage(**m) for m in msgs[-limit:]]

    def _write(self, session_id: str, doc: dict[str, Any]) -> None:
        with self._path(session_id).open("w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2, ensure_ascii=False)
