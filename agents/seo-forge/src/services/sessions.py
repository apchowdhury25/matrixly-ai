"""Chat session persistence."""

from __future__ import annotations

import json
from pathlib import Path

from ..models import ChatMessage, ChatSession, new_id, utc_now


class SessionStore:
    def __init__(self, data_dir: str | Path) -> None:
        self.dir = Path(data_dir) / "sessions"
        self.dir.mkdir(parents=True, exist_ok=True)

    def _path(self, session_id: str) -> Path:
        return self.dir / f"{session_id}.json"

    def get(self, session_id: str) -> ChatSession | None:
        p = self._path(session_id)
        if not p.exists():
            return None
        with p.open(encoding="utf-8") as f:
            return ChatSession(**json.load(f))

    def save(self, session: ChatSession) -> ChatSession:
        session.updated_at = utc_now()
        with self._path(session.id).open("w", encoding="utf-8") as f:
            json.dump(session.model_dump(), f, indent=2, ensure_ascii=False)
        return session

    def create(self, profile: dict | None = None) -> ChatSession:
        session = ChatSession(id=new_id("sess_"), profile=profile or {})
        return self.save(session)

    def append(
        self,
        session: ChatSession,
        role: str,
        content: str,
        meta: dict | None = None,
    ) -> ChatSession:
        session.messages.append(
            ChatMessage(role=role, content=content, meta=meta or {})
        )
        return self.save(session)
