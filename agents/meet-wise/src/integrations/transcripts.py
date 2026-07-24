"""Fetch or normalize transcripts from upload / Zoom / Teams / Google stubs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx


def load_upload(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    text = path.read_text(encoding="utf-8", errors="ignore")
    platform = "upload"
    low = text.lower()
    if "zoom" in low:
        platform = "zoom"
    elif "teams" in low or "microsoft" in low:
        platform = "teams"
    elif "google meet" in low or "meet.google" in low:
        platform = "google"
    return {"transcript": text, "platform": platform, "filename": path.name}


def fetch_zoom_transcript(cfg: dict, meeting_id: str = "") -> dict[str, Any]:
    """Optional Zoom cloud recording transcript fetch (soft-fail)."""
    z = cfg.get("zoom") or {}
    token = z.get("jwt_token") or ""
    if not token:
        return {"ok": False, "reason": "Zoom not configured — use transcript upload"}
    # Placeholder: real impl uses OAuth account credentials + recording APIs
    try:
        with httpx.Client(timeout=30.0) as client:
            # Illustrative endpoint; production needs proper Zoom OAuth + recording id
            resp = client.get(
                f"https://api.zoom.us/v2/meetings/{meeting_id}/recordings",
                headers={"Authorization": f"Bearer {token}"},
            )
            if not resp.is_success:
                return {"ok": False, "reason": f"Zoom HTTP {resp.status_code}"}
            return {"ok": True, "data": resp.json(), "transcript": ""}
    except Exception as e:
        return {"ok": False, "reason": str(e)}


def fetch_teams_transcript(cfg: dict, online_meeting_id: str = "") -> dict[str, Any]:
    """Optional Microsoft Graph transcript stub."""
    t = cfg.get("teams") or {}
    if not (t.get("tenant_id") and t.get("client_id") and t.get("client_secret")):
        return {"ok": False, "reason": "Teams not configured — use transcript upload"}
    return {
        "ok": False,
        "reason": "Teams Graph transcript fetch requires app consent; use upload for MVP",
        "hint": "Export VTT/TXT from Teams and POST /v1/process or upload file",
    }


def fetch_google_transcript(cfg: dict) -> dict[str, Any]:
    """Optional Google Meet/Drive export stub."""
    g = cfg.get("google") or {}
    token_path = Path(g.get("token_path") or "token.json")
    if not token_path.exists():
        return {"ok": False, "reason": "Google token missing — use transcript upload"}
    return {
        "ok": False,
        "reason": "Google Meet transcripts typically arrive via Drive export; use upload",
    }
