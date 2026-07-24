"""Document + version persistence."""

from __future__ import annotations

import json
from pathlib import Path

from ..models import DocVersion, Document, utc_now


class DocStore:
    def __init__(self, data_dir: str | Path) -> None:
        data_dir = Path(data_dir)
        self.dir = data_dir / "docs"
        self.versions = data_dir / "versions"
        self.exports = data_dir / "exports"
        for d in (self.dir, self.versions, self.exports):
            d.mkdir(parents=True, exist_ok=True)

    def save(self, doc: Document) -> Document:
        doc.updated_at = utc_now()
        path = self.dir / f"{doc.id}.json"
        path.write_text(json.dumps(doc.model_dump(), indent=2, ensure_ascii=False), encoding="utf-8")
        # version snapshot
        vpath = self.versions / f"{doc.id}_v{doc.version}.json"
        snap = DocVersion(
            version=doc.version,
            status=doc.status.value,
            body_markdown=doc.body_markdown,
            summary=doc.summary,
            created_by="system",
            note=f"status={doc.status.value}",
            export_paths=list(doc.export_paths),
        )
        vpath.write_text(json.dumps(snap.model_dump(), indent=2), encoding="utf-8")
        return doc

    def get(self, doc_id: str) -> Document | None:
        p = self.dir / f"{doc_id}.json"
        if not p.exists():
            return None
        return Document(**json.loads(p.read_text(encoding="utf-8")))

    def list(self, status: str | None = None, limit: int = 50) -> list[Document]:
        items: list[Document] = []
        for p in sorted(self.dir.glob("*.json"), reverse=True):
            try:
                doc = Document(**json.loads(p.read_text(encoding="utf-8")))
            except Exception:
                continue
            if status and doc.status.value != status:
                continue
            items.append(doc)
            if len(items) >= limit:
                break
        return items

    def list_versions(self, doc_id: str) -> list[dict]:
        out = []
        for p in sorted(self.versions.glob(f"{doc_id}_v*.json")):
            try:
                out.append(json.loads(p.read_text(encoding="utf-8")))
            except Exception:
                continue
        return out
