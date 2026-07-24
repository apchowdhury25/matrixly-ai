"""Persistent brand voice memory (file-backed)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..config import brand_voice_text
from ..models import utc_now


class BrandMemory:
    """Loads brand/voice.md and optional learned notes under data/memory/."""

    def __init__(self, data_dir: str | Path, cfg: dict) -> None:
        self.cfg = cfg
        self.dir = Path(data_dir) / "memory"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.notes_path = self.dir / "notes.json"

    def voice(self) -> str:
        return brand_voice_text(self.cfg)

    def notes(self) -> list[dict[str, Any]]:
        if not self.notes_path.exists():
            return []
        try:
            data = json.loads(self.notes_path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def add_note(self, note: str, source: str = "operator") -> dict[str, Any]:
        row = {"ts": utc_now(), "source": source, "note": note.strip()}
        items = self.notes()
        items.append(row)
        self.notes_path.write_text(json.dumps(items, indent=2), encoding="utf-8")
        return row

    def context_block(self) -> str:
        parts = [self.voice()]
        notes = self.notes()[-20:]
        if notes:
            parts.append("\n## Learned notes\n")
            for n in notes:
                parts.append(f"- {n.get('note')}")
        return "\n".join(parts)
