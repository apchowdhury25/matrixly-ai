"""Persistent pack settings (enable toggles + connection stubs)."""

from __future__ import annotations

import json
from pathlib import Path

from ..models import PackSettings, utc_now


class SettingsStore:
    def __init__(self, data_dir: str | Path) -> None:
        self.path = Path(data_dir) / "settings" / "pack.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> PackSettings:
        if not self.path.exists():
            s = PackSettings()
            self.save(s)
            return s
        try:
            return PackSettings(**json.loads(self.path.read_text(encoding="utf-8")))
        except Exception:
            return PackSettings()

    def save(self, settings: PackSettings) -> PackSettings:
        settings.updated_at = utc_now()
        self.path.write_text(
            json.dumps(settings.model_dump(), indent=2),
            encoding="utf-8",
        )
        return settings

    def update(
        self,
        *,
        agents_enabled: dict[str, bool] | None = None,
        connections: dict | None = None,
    ) -> PackSettings:
        s = self.load()
        if agents_enabled is not None:
            s.agents_enabled = {**s.agents_enabled, **agents_enabled}
        if connections is not None:
            s.connections = {**s.connections, **connections}
        return self.save(s)
