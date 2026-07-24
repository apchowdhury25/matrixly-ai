"""Optional Notion knowledge sync — export pages to knowledge/*.md."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx


def sync_notion_database(cfg: dict, knowledge_dir: str | Path) -> dict[str, Any]:
    """
    Fetch a Notion database and write markdown stubs into knowledge_dir.
    Requires NOTION_API_KEY + NOTION_DATABASE_ID.
    """
    notion = cfg.get("notion") or {}
    key = notion.get("api_key") or ""
    db = notion.get("database_id") or ""
    if not key or not db:
        return {"ok": False, "reason": "Notion not configured"}

    knowledge_dir = Path(knowledge_dir)
    knowledge_dir.mkdir(parents=True, exist_ok=True)

    headers = {
        "Authorization": f"Bearer {key}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    url = f"https://api.notion.com/v1/databases/{db}/query"
    written = 0
    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(url, headers=headers, json={})
            resp.raise_for_status()
            data = resp.json()
        for page in data.get("results") or []:
            title = _page_title(page) or page.get("id", "page")
            # Minimal body: properties dump as text (full block fetch is Phase 2)
            props = page.get("properties") or {}
            lines = [f"# {title}", "", f"Source: Notion page `{page.get('id')}`", ""]
            for name, prop in props.items():
                val = _prop_text(prop)
                if val:
                    lines.append(f"**{name}:** {val}")
            safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in title)[:60]
            path = knowledge_dir / f"notion_{safe}.md"
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            written += 1
        return {"ok": True, "pages": written}
    except Exception as e:
        return {"ok": False, "reason": str(e)}


def _page_title(page: dict[str, Any]) -> str:
    props = page.get("properties") or {}
    for prop in props.values():
        if prop.get("type") == "title":
            parts = prop.get("title") or []
            return "".join(p.get("plain_text", "") for p in parts)
    return ""


def _prop_text(prop: dict[str, Any]) -> str:
    t = prop.get("type")
    if t == "title":
        return "".join(p.get("plain_text", "") for p in prop.get("title") or [])
    if t == "rich_text":
        return "".join(p.get("plain_text", "") for p in prop.get("rich_text") or [])
    if t == "select" and prop.get("select"):
        return prop["select"].get("name") or ""
    if t == "multi_select":
        return ", ".join(x.get("name", "") for x in prop.get("multi_select") or [])
    if t == "number" and prop.get("number") is not None:
        return str(prop["number"])
    if t == "url":
        return prop.get("url") or ""
    return ""
