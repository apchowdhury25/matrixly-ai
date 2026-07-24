"""Meeting persistence + exports."""

from __future__ import annotations

import json
from pathlib import Path

from ..models import Meeting, utc_now


class MeetingStore:
    def __init__(self, data_dir: str | Path) -> None:
        data_dir = Path(data_dir)
        self.dir = data_dir / "meetings"
        self.exports = data_dir / "exports"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.exports.mkdir(parents=True, exist_ok=True)

    def _path(self, meeting_id: str) -> Path:
        return self.dir / f"{meeting_id}.json"

    def save(self, meeting: Meeting) -> Meeting:
        meeting.updated_at = utc_now()
        with self._path(meeting.id).open("w", encoding="utf-8") as f:
            json.dump(meeting.model_dump(), f, indent=2, ensure_ascii=False)
        return meeting

    def get(self, meeting_id: str) -> Meeting | None:
        p = self._path(meeting_id)
        if not p.exists():
            return None
        with p.open(encoding="utf-8") as f:
            return Meeting(**json.load(f))

    def list(self, status: str | None = None, limit: int = 50) -> list[Meeting]:
        items: list[Meeting] = []
        for p in sorted(self.dir.glob("*.json"), reverse=True):
            try:
                with p.open(encoding="utf-8") as f:
                    m = Meeting(**json.load(f))
            except Exception:
                continue
            if status and m.status.value != status:
                continue
            items.append(m)
            if len(items) >= limit:
                break
        return items

    def export(self, meeting: Meeting) -> list[str]:
        base = self.exports / meeting.id
        base.mkdir(parents=True, exist_ok=True)
        paths: list[str] = []

        def w(name: str, text: str) -> None:
            p = base / name
            p.write_text(text, encoding="utf-8")
            paths.append(str(p))

        w(
            "summary.md",
            f"# {meeting.title or meeting.id}\n\n"
            f"{meeting.summary}\n\n"
            f"## Decisions\n"
            + "\n".join(f"- {d}" for d in meeting.decisions)
            + "\n\n## Discussion\n"
            + "\n".join(f"- {d}" for d in meeting.discussion_points)
            + "\n",
        )
        actions_md = "# Action items\n\n"
        for a in meeting.action_items:
            actions_md += (
                f"- **{a.description}** · owner={a.owner or 'TBD'} "
                f"· due={a.deadline or 'TBD'} · {a.priority}\n"
            )
        if meeting.follow_ups:
            actions_md += "\n## Follow-ups\n" + "\n".join(f"- {f}" for f in meeting.follow_ups) + "\n"
        w("actions.md", actions_md)
        w("crm.json", json.dumps(meeting.crm_payload, indent=2, ensure_ascii=False))
        w(
            "recap.md",
            f"Subject: {meeting.recap_subject}\n\n{meeting.recap_body}\n",
        )
        w("meeting.json", json.dumps(meeting.model_dump(), indent=2, ensure_ascii=False))
        meeting.export_paths = paths
        self.save(meeting)
        return paths
