"""Optional Notion page creation (free user token — never required for analysis)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx

from ..models import AnalysisReport, utc_now


class NotionExporter:
    def __init__(self, data_dir: str | Path, cfg: dict) -> None:
        self.cfg = cfg
        self.dir = Path(data_dir) / "notion"
        self.dir.mkdir(parents=True, exist_ok=True)
        notion = cfg.get("notion") or {}
        self.api_key = notion.get("api_key") or ""
        self.parent = notion.get("parent_page_id") or ""
        self.enabled = bool(notion.get("enabled") and self.api_key and self.parent)

    def save(self, report: AnalysisReport) -> dict[str, Any]:
        payload = {
            "ticker": report.ticker,
            "as_of": report.as_of,
            "title": f"ETF Analysis — {report.ticker} — {report.as_of}",
            "markdown": report.markdown,
            "takeaway": report.takeaway,
            "ts": utc_now(),
        }
        # Always log locally
        local = self.dir / f"{report.id}.json"
        local.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        md_path = self.dir / f"{report.id}.md"
        md_path.write_text(report.markdown or "", encoding="utf-8")

        if not self.enabled:
            return {
                "ok": True,
                "backend": "local",
                "path": str(local),
                "note": "Notion not configured — saved locally under data/notion/. Set NOTION_API_KEY + NOTION_PARENT_PAGE_ID to push live.",
            }

        # Create page via Notion API
        children = _markdown_to_blocks(report.markdown or report.takeaway or report.ticker)
        body = {
            "parent": {"page_id": self.parent.replace("-", "")},
            "properties": {
                "title": {
                    "title": [{"text": {"content": payload["title"][:200]}}],
                }
            },
            "children": children[:100],
        }
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(
                    "https://api.notion.com/v1/pages",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Notion-Version": "2022-06-28",
                        "Content-Type": "application/json",
                    },
                    json=body,
                )
            ok = resp.status_code < 400
            data = resp.json() if resp.content else {}
            page_id = data.get("id")
            url = data.get("url")
            result = {
                "ok": ok,
                "backend": "notion",
                "status_code": resp.status_code,
                "page_id": page_id,
                "url": url,
                "local_path": str(local),
            }
            if not ok:
                result["body"] = resp.text[:400]
                result["note"] = "Notion API error — local copy retained."
            return result
        except Exception as e:
            return {
                "ok": False,
                "backend": "notion",
                "error": str(e),
                "local_path": str(local),
            }


def _markdown_to_blocks(md: str) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for line in md.splitlines():
        line = line.rstrip()
        if not line:
            continue
        if line.startswith("# "):
            blocks.append(_heading(line[2:], 1))
        elif line.startswith("## "):
            blocks.append(_heading(line[3:], 2))
        elif line.startswith("### "):
            blocks.append(_heading(line[4:], 3))
        elif line.startswith("- "):
            blocks.append(
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": line[2:][:2000]}}]
                    },
                }
            )
        else:
            blocks.append(
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": line[:2000]}}]
                    },
                }
            )
    if not blocks:
        blocks.append(
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": "ETF analysis"}}]},
            }
        )
    return blocks


def _heading(text: str, level: int) -> dict[str, Any]:
    key = f"heading_{min(max(level, 1), 3)}"
    return {
        "object": "block",
        "type": key,
        key: {"rich_text": [{"type": "text", "text": {"content": text[:2000]}}]},
    }
