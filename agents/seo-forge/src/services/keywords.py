"""Keyword tracker persistence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..models import KeywordItem, utc_now


class KeywordStore:
    def __init__(self, data_dir: str | Path) -> None:
        self.path = Path(data_dir) / "keywords" / "tracker.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({"updated_at": utc_now(), "items": []})

    def _read(self) -> dict[str, Any]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {"updated_at": utc_now(), "items": []}

    def _write(self, data: dict[str, Any]) -> None:
        data["updated_at"] = utc_now()
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def list(self) -> list[dict[str, Any]]:
        return list(self._read().get("items") or [])

    def upsert(self, items: list[KeywordItem]) -> list[dict[str, Any]]:
        data = self._read()
        by_key = {
            (str(i.get("keyword") or "").lower(), str(i.get("city") or "").lower()): i
            for i in (data.get("items") or [])
        }
        for item in items:
            key = (item.keyword.lower().strip(), (item.city or "").lower().strip())
            existing = by_key.get(key) or {}
            row = item.model_dump()
            if existing.get("current_rank") is not None and row.get("previous_rank") is None:
                if row.get("current_rank") != existing.get("current_rank"):
                    row["previous_rank"] = existing.get("current_rank")
            by_key[key] = {**existing, **row}
        data["items"] = list(by_key.values())
        self._write(data)
        return data["items"]

    def remove(self, keyword: str, city: str = "") -> bool:
        data = self._read()
        before = len(data.get("items") or [])
        data["items"] = [
            i
            for i in (data.get("items") or [])
            if not (
                str(i.get("keyword") or "").lower() == keyword.lower()
                and str(i.get("city") or "").lower() == city.lower()
            )
        ]
        self._write(data)
        return len(data["items"]) < before

    def summary(self) -> dict[str, Any]:
        items = self.list()
        improved = 0
        for i in items:
            cur = i.get("current_rank")
            prev = i.get("previous_rank")
            if isinstance(cur, int) and isinstance(prev, int) and cur < prev:
                improved += 1
        return {
            "total": len(items),
            "tracking": len([i for i in items if i.get("status") == "tracking"]),
            "improved": improved,
            "high_priority": len([i for i in items if i.get("priority") == "high"]),
        }
