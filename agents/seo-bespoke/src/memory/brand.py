"""Brand voice memory for SEO-Bespoke factory."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class BrandMemory:
    def __init__(self, cfg: dict[str, Any]) -> None:
        self.cfg = cfg
        brand_dir = Path(cfg["paths"]["brand"])
        self.voice_path = brand_dir / "voice.md"
        self.meta_path = Path(cfg["paths"]["data"]) / "memory" / "brand.json"
        self.meta_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.meta_path.exists():
            self.meta_path.write_text(
                json.dumps({"tone": (cfg.get("brand") or {}).get("tone") or [], "avoid": (cfg.get("brand") or {}).get("avoid") or []}, indent=2),
                encoding="utf-8",
            )

    def get_voice_markdown(self) -> str:
        if self.voice_path.exists():
            return self.voice_path.read_text(encoding="utf-8")
        return ""

    def save_voice(
        self,
        voice_markdown: str,
        tone: list[str] | None = None,
        avoid: list[str] | None = None,
    ) -> dict[str, Any]:
        self.voice_path.parent.mkdir(parents=True, exist_ok=True)
        self.voice_path.write_text(voice_markdown, encoding="utf-8")
        meta = json.loads(self.meta_path.read_text(encoding="utf-8")) if self.meta_path.exists() else {}
        if tone is not None:
            meta["tone"] = tone
        if avoid is not None:
            meta["avoid"] = avoid
        self.meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        return {"ok": True, "tone": meta.get("tone"), "avoid": meta.get("avoid")}

    def meta(self) -> dict[str, Any]:
        if self.meta_path.exists():
            return json.loads(self.meta_path.read_text(encoding="utf-8"))
        return {}
