"""Persistent scoring playbook notes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..models import utc_now


class PlaybookMemory:
    def __init__(self, data_dir: str | Path, cfg: dict) -> None:
        self.cfg = cfg
        self.dir = Path(data_dir) / "memory"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / "playbook_notes.json"

    def notes(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def add_note(self, note: str, source: str = "operator") -> dict[str, Any]:
        row = {"ts": utc_now(), "source": source, "note": note.strip()}
        items = self.notes()
        items.append(row)
        self.path.write_text(json.dumps(items, indent=2), encoding="utf-8")
        return row

    def context(self) -> str:
        scoring = self.cfg.get("scoring") or {}
        lines = [
            f"Weights: {scoring.get('weights')}",
            f"Hot min: {scoring.get('hot_min')}, Warm min: {scoring.get('warm_min')}",
            f"Stale days: {scoring.get('stale_days')}",
        ]
        for n in self.notes()[-15:]:
            lines.append(f"- {n.get('note')}")
        return "\n".join(lines)
