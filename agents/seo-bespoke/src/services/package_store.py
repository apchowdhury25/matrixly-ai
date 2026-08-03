"""Generated custom agent package registry."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..models import utc_now


class PackageStore:
    def __init__(self, data_dir: str | Path) -> None:
        self.dir = Path(data_dir) / "packages"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.dir / "index.json"
        if not self.index_path.exists():
            self._write_index({"packages": []})

    def _write_index(self, data: dict[str, Any]) -> None:
        with self.index_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _read_index(self) -> dict[str, Any]:
        with self.index_path.open(encoding="utf-8") as f:
            return json.load(f)

    def register(self, package: dict[str, Any]) -> dict[str, Any]:
        data = self._read_index()
        package = {**package, "registered_at": utc_now()}
        packages = [p for p in data.get("packages") or [] if p.get("id") != package.get("id")]
        packages.insert(0, package)
        data["packages"] = packages[:100]
        self._write_index(data)
        return package

    def list(self, limit: int = 50) -> list[dict[str, Any]]:
        return (self._read_index().get("packages") or [])[:limit]

    def get(self, package_id: str) -> dict[str, Any] | None:
        for p in self.list(limit=100):
            if p.get("id") == package_id:
                return p
        return None

    def package_dir(self, package_id: str) -> Path:
        d = self.dir / package_id
        d.mkdir(parents=True, exist_ok=True)
        return d
