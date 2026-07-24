"""Send or log recap emails."""

from __future__ import annotations

import json
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import Any

from ..models import Meeting, utc_now


class RecapMailer:
    def __init__(self, data_dir: str | Path, cfg: dict) -> None:
        self.dir = Path(data_dir) / "emails"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.cfg = cfg

    def send(
        self,
        meeting: Meeting,
        to_addrs: list[str] | None = None,
    ) -> dict[str, Any]:
        to_addrs = to_addrs or []
        backend = ((self.cfg.get("email") or {}).get("backend") or "log").lower()
        record = {
            "meeting_id": meeting.id,
            "subject": meeting.recap_subject,
            "body": meeting.recap_body,
            "to": to_addrs,
            "ts": utc_now(),
            "backend": backend,
        }
        path = self.dir / f"{meeting.id}_recap.json"
        path.write_text(json.dumps(record, indent=2), encoding="utf-8")

        if backend == "smtp" and to_addrs:
            smtp = self.cfg.get("smtp") or {}
            if not (smtp.get("host") and smtp.get("from_addr")):
                return {"ok": True, "backend": "log", "path": str(path), "note": "SMTP incomplete"}
            try:
                msg = EmailMessage()
                msg["Subject"] = meeting.recap_subject
                msg["From"] = smtp["from_addr"]
                msg["To"] = ", ".join(to_addrs)
                msg.set_content(meeting.recap_body)
                with smtplib.SMTP(smtp["host"], int(smtp.get("port") or 587)) as s:
                    s.starttls()
                    if smtp.get("user"):
                        s.login(smtp["user"], smtp.get("password") or "")
                    s.send_message(msg)
                return {"ok": True, "backend": "smtp", "to": to_addrs, "path": str(path)}
            except Exception as e:
                return {"ok": False, "backend": "smtp", "reason": str(e), "path": str(path)}

        return {"ok": True, "backend": "log", "path": str(path), "to": to_addrs}
