"""Business SEO Profile persistence."""

from __future__ import annotations

import json
from pathlib import Path

from ..models import BusinessSeoProfile, utc_now


class ProfileStore:
    def __init__(self, data_dir: str | Path) -> None:
        self.dir = Path(data_dir) / "profiles"
        self.dir.mkdir(parents=True, exist_ok=True)

    def _path(self, profile_id: str) -> Path:
        return self.dir / f"{profile_id}.json"

    def save(self, profile: BusinessSeoProfile) -> BusinessSeoProfile:
        profile.updated_at = utc_now()
        with self._path(profile.id).open("w", encoding="utf-8") as f:
            json.dump(profile.model_dump(), f, indent=2, ensure_ascii=False)
        md = self.dir / f"{profile.id}.md"
        if profile.summary_markdown:
            md.write_text(profile.summary_markdown, encoding="utf-8")
        return profile

    def get(self, profile_id: str) -> BusinessSeoProfile | None:
        p = self._path(profile_id)
        if not p.exists():
            return None
        with p.open(encoding="utf-8") as f:
            return BusinessSeoProfile(**json.load(f))

    def list(self, limit: int = 50) -> list[BusinessSeoProfile]:
        items: list[BusinessSeoProfile] = []
        for p in sorted(self.dir.glob("*.json"), reverse=True):
            try:
                with p.open(encoding="utf-8") as f:
                    items.append(BusinessSeoProfile(**json.load(f)))
            except Exception:
                continue
            if len(items) >= limit:
                break
        return items

    def latest(self) -> BusinessSeoProfile | None:
        items = self.list(limit=1)
        return items[0] if items else None
