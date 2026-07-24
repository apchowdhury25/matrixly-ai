"""Apply CRM payload to local Salesforce-shaped store (JSON/CSV)."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from ..models import Meeting, utc_now


class CrmWriter:
    def __init__(self, data_dir: str | Path, cfg: dict) -> None:
        self.dir = Path(data_dir) / "crm"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.cfg = cfg
        self.opp_path = self.dir / "opportunities.json"
        self.tasks_path = self.dir / "tasks.json"
        self.notes_path = self.dir / "notes.json"
        self.tasks_csv = self.dir / "tasks.csv"

    def apply(self, meeting: Meeting) -> dict[str, Any]:
        payload = meeting.crm_payload or {}
        opps = _load_list(self.opp_path)
        tasks = _load_list(self.tasks_path)
        notes = _load_list(self.notes_path)

        opp = payload.get("opportunity") or {}
        if opp and (opp.get("name") or opp.get("notes")):
            row = {
                "Id": f"opp_{meeting.id}",
                "Name": opp.get("name"),
                "StageName": opp.get("stage"),
                "Amount": opp.get("amount"),
                "NextStep": opp.get("next_step"),
                "Description": opp.get("notes"),
                "MeetingId": meeting.id,
                "UpdatedAt": utc_now(),
            }
            opps = [o for o in opps if o.get("MeetingId") != meeting.id]
            opps.append(row)

        for t in payload.get("tasks") or []:
            tasks.append(
                {
                    "Id": f"task_{meeting.id}_{len(tasks)}",
                    "Subject": t.get("subject"),
                    "OwnerEmail": t.get("owner_email"),
                    "ActivityDate": t.get("due_date"),
                    "Status": t.get("status") or "Not Started",
                    "Priority": t.get("priority") or "Normal",
                    "Description": t.get("description"),
                    "WhatId": f"opp_{meeting.id}" if opp else None,
                    "MeetingId": meeting.id,
                    "CreatedAt": utc_now(),
                }
            )

        for n in payload.get("notes") or []:
            notes.append(
                {
                    "Id": f"note_{meeting.id}_{len(notes)}",
                    "Title": n.get("title"),
                    "Body": n.get("body"),
                    "MeetingId": meeting.id,
                    "CreatedAt": utc_now(),
                }
            )

        _save_list(self.opp_path, opps)
        _save_list(self.tasks_path, tasks)
        _save_list(self.notes_path, notes)
        self._write_tasks_csv(tasks)
        return {
            "ok": True,
            "opportunities": len(opps),
            "tasks": len([t for t in tasks if t.get("MeetingId") == meeting.id]),
            "notes": len([n for n in notes if n.get("MeetingId") == meeting.id]),
            "paths": [str(self.opp_path), str(self.tasks_path), str(self.notes_path), str(self.tasks_csv)],
        }

    def _write_tasks_csv(self, tasks: list[dict[str, Any]]) -> None:
        fields = [
            "Id",
            "Subject",
            "OwnerEmail",
            "ActivityDate",
            "Status",
            "Priority",
            "Description",
            "MeetingId",
            "CreatedAt",
        ]
        with self.tasks_csv.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            for t in tasks:
                w.writerow({k: t.get(k, "") for k in fields})


def _load_list(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_list(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
