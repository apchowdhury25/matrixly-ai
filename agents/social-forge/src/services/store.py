"""Campaign, schedule, inbox, insights persistence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..models import Campaign, InboxItem, InsightsReport, utc_now


class SocialStore:
    def __init__(self, data_dir: str | Path) -> None:
        data_dir = Path(data_dir)
        self.posts = data_dir / "posts"
        self.schedule_dir = data_dir / "schedule"
        self.inbox_dir = data_dir / "inbox"
        self.insights_dir = data_dir / "insights"
        self.exports = data_dir / "exports"
        for d in (
            self.posts,
            self.schedule_dir,
            self.inbox_dir,
            self.insights_dir,
            self.exports,
        ):
            d.mkdir(parents=True, exist_ok=True)

    def save_campaign(self, c: Campaign) -> Campaign:
        c.updated_at = utc_now()
        path = self.posts / f"{c.id}.json"
        path.write_text(json.dumps(c.model_dump(), indent=2, ensure_ascii=False), encoding="utf-8")
        return c

    def get_campaign(self, campaign_id: str) -> Campaign | None:
        p = self.posts / f"{campaign_id}.json"
        if not p.exists():
            return None
        return Campaign(**json.loads(p.read_text(encoding="utf-8")))

    def list_campaigns(self, status: str | None = None, limit: int = 50) -> list[Campaign]:
        items: list[Campaign] = []
        for p in sorted(self.posts.glob("*.json"), reverse=True):
            try:
                c = Campaign(**json.loads(p.read_text(encoding="utf-8")))
            except Exception:
                continue
            if status and c.status.value != status:
                continue
            items.append(c)
            if len(items) >= limit:
                break
        return items

    def export_campaign(self, c: Campaign) -> list[str]:
        base = self.exports / c.id
        base.mkdir(parents=True, exist_ok=True)
        paths: list[str] = []

        def write(name: str, text: str) -> None:
            p = base / name
            p.write_text(text, encoding="utf-8")
            paths.append(str(p))

        for platform, post in (c.posts or {}).items():
            body = post.text
            if post.hashtags:
                tags = " ".join(post.hashtags)
                if tags not in body:
                    body = f"{body}\n\n{tags}"
            if post.thread:
                body += "\n\n--- thread ---\n" + "\n\n".join(
                    f"{i+1}/ {t}" for i, t in enumerate(post.thread)
                )
            write(f"{platform}.txt", body)

        write(
            "schedule.json",
            json.dumps(c.schedule, indent=2, ensure_ascii=False),
        )
        write("campaign.json", json.dumps(c.model_dump(), indent=2, ensure_ascii=False))
        c.export_paths = paths
        self.save_campaign(c)
        return paths

    def save_schedule_item(self, item: dict[str, Any]) -> Path:
        sid = item.get("id") or f"sch_{utc_now().replace(':', '').replace('-', '')[:16]}"
        item["id"] = sid
        path = self.schedule_dir / f"{sid}.json"
        path.write_text(json.dumps(item, indent=2), encoding="utf-8")
        return path

    def list_schedule(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for p in sorted(self.schedule_dir.glob("*.json")):
            try:
                out.append(json.loads(p.read_text(encoding="utf-8")))
            except Exception:
                continue
        return out

    def save_inbox(self, item: InboxItem) -> InboxItem:
        path = self.inbox_dir / f"{item.id}.json"
        path.write_text(json.dumps(item.model_dump(), indent=2, ensure_ascii=False), encoding="utf-8")
        return item

    def get_inbox(self, inbox_id: str) -> InboxItem | None:
        p = self.inbox_dir / f"{inbox_id}.json"
        if not p.exists():
            return None
        return InboxItem(**json.loads(p.read_text(encoding="utf-8")))

    def list_inbox(self, status: str | None = None, limit: int = 100) -> list[InboxItem]:
        items: list[InboxItem] = []
        for p in sorted(self.inbox_dir.glob("*.json"), reverse=True):
            try:
                it = InboxItem(**json.loads(p.read_text(encoding="utf-8")))
            except Exception:
                continue
            if status and it.status != status:
                continue
            items.append(it)
            if len(items) >= limit:
                break
        return items

    def save_insights(self, report: InsightsReport) -> InsightsReport:
        path = self.insights_dir / f"{report.id}.json"
        path.write_text(
            json.dumps(report.model_dump(), indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return report

    def latest_insights(self) -> InsightsReport | None:
        files = sorted(self.insights_dir.glob("*.json"), reverse=True)
        if not files:
            return None
        return InsightsReport(**json.loads(files[0].read_text(encoding="utf-8")))
