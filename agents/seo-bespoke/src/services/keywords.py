"""Keyword tracker (owner-supplied ranks only — never invent rankings)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..models import KeywordItem


class KeywordStore:
    def __init__(self, data_dir: str | Path) -> None:
        self.path = Path(data_dir) / "keywords" / "tracker.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({"keywords": []})

    def _read(self) -> dict[str, Any]:
        with self.path.open(encoding="utf-8") as f:
            return json.load(f)

    def _write(self, data: dict[str, Any]) -> None:
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def list(self) -> list[KeywordItem]:
        data = self._read()
        return [KeywordItem(**k) for k in data.get("keywords") or []]

    def upsert(self, items: list[KeywordItem]) -> list[KeywordItem]:
        existing = {k.keyword.lower(): k for k in self.list()}
        for item in items:
            key = item.keyword.strip().lower()
            if not key:
                continue
            prev = existing.get(key)
            if prev and item.current_rank is not None and prev.current_rank is not None:
                if item.previous_rank is None:
                    item.previous_rank = prev.current_rank
            existing[key] = item
        all_items = list(existing.values())
        self._write({"keywords": [k.model_dump() for k in all_items]})
        return all_items

    def summary(self) -> dict[str, Any]:
        items = self.list()
        improved = 0
        for k in items:
            if (
                k.current_rank is not None
                and k.previous_rank is not None
                and k.current_rank < k.previous_rank
            ):
                improved += 1
        return {
            "total": len(items),
            "tracking": sum(1 for k in items if k.status == "tracking"),
            "improved": improved,
            "note": "Ranks are owner-supplied only. SEO-Bespoke never invents rankings.",
        }
