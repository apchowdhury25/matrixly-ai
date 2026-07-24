"""Persistent brand + clause memory."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..config import brand_text
from ..models import utc_now


class BrandMemory:
    def __init__(self, data_dir: str | Path, cfg: dict) -> None:
        self.cfg = cfg
        self.dir = Path(data_dir) / "memory"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.notes_path = self.dir / "notes.json"
        self.clauses_path = self.dir / "clauses.json"

    def guidelines(self) -> str:
        return brand_text(self.cfg)

    def notes(self) -> list[dict[str, Any]]:
        return self._read_list(self.notes_path)

    def clauses(self) -> list[dict[str, Any]]:
        return self._read_list(self.clauses_path)

    def add_note(self, note: str, source: str = "operator") -> dict[str, Any]:
        row = {"ts": utc_now(), "source": source, "note": note.strip()}
        items = self.notes()
        items.append(row)
        self.notes_path.write_text(json.dumps(items, indent=2), encoding="utf-8")
        return row

    def add_clause(self, name: str, body: str) -> dict[str, Any]:
        row = {"ts": utc_now(), "name": name.strip(), "body": body.strip()}
        items = self.clauses()
        items.append(row)
        self.clauses_path.write_text(json.dumps(items, indent=2), encoding="utf-8")
        return row

    def context(self) -> str:
        parts = [self.guidelines(), "\n## Operator notes\n"]
        for n in self.notes()[-15:]:
            parts.append(f"- {n.get('note')}")
        clauses = self.clauses()[-10:]
        if clauses:
            parts.append("\n## Approved clauses\n")
            for c in clauses:
                parts.append(f"### {c.get('name')}\n{c.get('body')}\n")
        return "\n".join(parts)

    def _read_list(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []
