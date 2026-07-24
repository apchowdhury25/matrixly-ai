"""Intake agent — normalize client/project data."""

from __future__ import annotations

from typing import Any

from .. import llm
from ..config import prompt_text
from ..models import ClientInfo, Document, DocType, LineItem, ProjectInfo


def run_intake(doc: Document, cfg: dict, raw: dict[str, Any] | None = None) -> tuple[Document, int, int]:
    tin = tout = 0
    raw = raw or {}

    if llm.grok_available(cfg) and raw:
        try:
            system = prompt_text("intake")
            user = f"Normalize this document request:\n{raw}"
            content, tin, tout = llm.chat(cfg, system, user)
            data = llm.extract_json(content)
            if isinstance(data, dict):
                _apply(doc, data, cfg)
                return doc, tin, tout
        except Exception as e:
            doc.metadata["intake_error"] = str(e)

    _apply(doc, raw or _from_doc(doc), cfg)
    return doc, tin, tout


def _from_doc(doc: Document) -> dict[str, Any]:
    return {
        "doc_type": doc.doc_type.value,
        "client": doc.client.model_dump(),
        "project": doc.project.model_dump(),
        "line_items": [li.model_dump() for li in doc.line_items],
        "notes": doc.metadata.get("notes") or "",
    }


def _apply(doc: Document, data: dict[str, Any], cfg: dict) -> None:
    dtype = str(data.get("doc_type") or doc.doc_type.value or "proposal").lower()
    try:
        doc.doc_type = DocType(dtype)
    except Exception:
        doc.doc_type = DocType.proposal

    client = data.get("client") or {}
    if isinstance(client, dict):
        doc.client = ClientInfo(
            name=str(client.get("name") or client.get("contact") or ""),
            contact=str(client.get("contact") or client.get("name") or ""),
            email=str(client.get("email") or ""),
            company=str(client.get("company") or client.get("name") or ""),
            industry=str(client.get("industry") or ""),
        )

    project = data.get("project") or {}
    if isinstance(project, dict):
        doc.project = ProjectInfo(
            title=str(project.get("title") or ""),
            summary=str(project.get("summary") or ""),
            goals=[str(g) for g in (project.get("goals") or [])],
            timeline=str(project.get("timeline") or ""),
            constraints=[str(c) for c in (project.get("constraints") or [])],
        )

    items = data.get("line_items") or []
    catalog = {(c.get("sku") or ""): c for c in ((cfg.get("pricing") or {}).get("catalog") or [])}
    line_items: list[LineItem] = []
    for row in items:
        if not isinstance(row, dict):
            continue
        sku = str(row.get("sku") or "")
        cat = catalog.get(sku) or {}
        line_items.append(
            LineItem(
                sku=sku,
                name=str(row.get("name") or cat.get("name") or sku or "Item"),
                qty=float(row.get("qty") or 1),
                unit_price=float(row.get("unit_price") if row.get("unit_price") is not None else cat.get("unit_price") or 0),
                unit=str(row.get("unit") or cat.get("unit") or ""),
            )
        )
    if line_items:
        doc.line_items = line_items
    if data.get("notes"):
        doc.metadata["notes"] = str(data["notes"])
    if not doc.project.title and doc.client.company:
        doc.project.title = f"{doc.doc_type.value.title()} for {doc.client.company}"
