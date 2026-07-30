"""Brand voice memory — train and persist client voice."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..config import ROOT, brand_voice_text
from ..models import utc_now


class BrandMemory:
    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg
        mem = Path(cfg["paths"]["memory"])
        mem.mkdir(parents=True, exist_ok=True)
        self.profile_path = mem / "profile.json"
        self.voice_override = mem / "voice_override.md"
        self.brand_file = ROOT / ((cfg.get("brand") or {}).get("voice_file") or "brand/voice.md")

    def get_voice(self) -> str:
        if self.voice_override.exists():
            return self.voice_override.read_text(encoding="utf-8")
        return brand_voice_text(self.cfg)

    def get_profile(self) -> dict[str, Any]:
        if self.profile_path.exists():
            try:
                return json.loads(self.profile_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        biz = self.cfg.get("business") or {}
        return {
            "business_name": biz.get("name") or "",
            "business_type": biz.get("industry") or "",
            "service_areas": biz.get("service_areas") or [],
            "website": biz.get("website") or "",
            "primary_goal": biz.get("primary_goal") or "organic_leads",
            "gbp_status": "",
            "updated_at": utc_now(),
        }

    def save_profile(self, profile: dict[str, Any]) -> dict[str, Any]:
        current = self.get_profile()
        current.update({k: v for k, v in profile.items() if v is not None})
        current["updated_at"] = utc_now()
        self.profile_path.write_text(json.dumps(current, indent=2), encoding="utf-8")
        return current

    def save_voice(
        self,
        voice_markdown: str,
        tone: list[str] | None = None,
        avoid: list[str] | None = None,
    ) -> dict[str, Any]:
        text = voice_markdown.strip()
        self.voice_override.write_text(text + "\n", encoding="utf-8")
        # Also mirror to brand/voice.md for prompt loaders that use config path
        try:
            self.brand_file.parent.mkdir(parents=True, exist_ok=True)
            self.brand_file.write_text(text + "\n", encoding="utf-8")
        except Exception:
            pass
        brand = dict(self.cfg.get("brand") or {})
        if tone:
            brand["tone"] = tone
        if avoid:
            brand["avoid"] = avoid
        self.cfg["brand"] = brand
        return {
            "ok": True,
            "chars": len(text),
            "tone": brand.get("tone") or [],
            "avoid": brand.get("avoid") or [],
            "updated_at": utc_now(),
        }
