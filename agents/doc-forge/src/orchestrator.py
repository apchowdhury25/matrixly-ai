"""Crew-style document pipeline: Intake → Legal → Draft → Brand check → Export → HITL."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .agents.brand_check import run_brand_check
from .agents.drafter import run_drafter
from .agents.intake import run_intake
from .agents.legal import run_legal
from .integrations.crm import ClientCrm
from .integrations.export import DocumentExporter
from .llm import cost_usd, grok_available
from .memory.brand import BrandMemory
from .models import (
    ClientInfo,
    Document,
    DocStatus,
    DocType,
    DocVersion,
    LineItem,
    ProjectInfo,
    new_id,
    utc_now,
)
from .services.audit import AuditLog
from .services.hitl import HitlQueue
from .services.store import DocStore
from .services.templates import TemplateStore
from .services.usage import UsageMeter


class DocForge:
    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg
        data = Path(cfg["paths"]["data"])
        self.store = DocStore(data)
        self.hitl = HitlQueue(data)
        self.audit = AuditLog(data)
        self.usage = UsageMeter(data, cfg)
        self.brand = BrandMemory(data, cfg)
        self.templates = TemplateStore(cfg["paths"]["templates"])
        self.exporter = DocumentExporter(data, cfg)
        self.crm = ClientCrm(data, cfg)
        self.samples = Path(cfg["paths"]["samples"])

    def draft(
        self,
        *,
        doc_type: str = "proposal",
        client: dict[str, Any] | None = None,
        project: dict[str, Any] | None = None,
        line_items: list[dict[str, Any]] | None = None,
        discount_pct: float = 0,
        notes: str = "",
        template_id: str = "",
        source: str = "manual",
        crm_account: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> Document:
        raw: dict[str, Any] = {
            "doc_type": doc_type,
            "client": client or {},
            "project": project or {},
            "line_items": line_items or [],
            "notes": notes,
        }

        if source == "sample":
            sample = self.samples / "client_brief.json"
            if sample.exists():
                raw = json.loads(sample.read_text(encoding="utf-8"))
        elif source == "crm" or crm_account:
            found = self.crm.get_client(crm_account or (client or {}).get("company", ""))
            if found:
                raw["client"] = {**(raw.get("client") or {}), **found}

        try:
            dtype = DocType(str(raw.get("doc_type") or doc_type).lower())
        except Exception:
            dtype = DocType.proposal

        doc = Document(
            id=new_id("doc_"),
            doc_type=dtype,
            status=DocStatus.received,
            discount_pct=float(raw.get("discount_pct") or discount_pct or 0),
            template_id=template_id or dtype.value,
            metadata=metadata or {"source": source, "notes": notes},
        )
        self.store.save(doc)
        self.audit.write("doc_received", document_id=doc.id, doc_type=doc.doc_type.value)

        tin = tout = 0

        doc, a, b = run_intake(doc, self.cfg, raw)
        tin += a
        tout += b
        self.store.save(doc)
        self.audit.write("intake", document_id=doc.id)

        doc, a, b = run_legal(doc, self.cfg, self.brand)
        tin += a
        tout += b
        self.store.save(doc)
        self.audit.write("legal", document_id=doc.id)

        doc, a, b = run_drafter(doc, self.cfg, self.brand, self.templates)
        tin += a
        tout += b
        self.store.save(doc)
        self.audit.write("drafted", document_id=doc.id, title=doc.title)

        doc, a, b = run_brand_check(doc, self.cfg, self.brand)
        tin += a
        tout += b

        paths = self.exporter.export(doc)
        doc.export_paths = paths
        doc.usage_tokens_in = tin
        doc.usage_tokens_out = tout
        doc.estimated_cost_usd = round(cost_usd(self.cfg, tin, tout), 6)

        # version record
        doc.versions.append(
            DocVersion(
                version=doc.version,
                status=doc.status.value,
                body_markdown=doc.body_markdown,
                summary=doc.summary,
                export_paths=list(paths),
                note="initial draft",
            )
        )

        require = (self.cfg.get("documents") or {}).get("require_hitl_before_send", True)
        mode = (self.cfg.get("hitl") or {}).get("mode") or "external_only"
        auto = (self.cfg.get("hitl") or {}).get("auto_approve")
        if require and mode != "off" and not auto:
            action = self.hitl.enqueue(
                kind="document_approval",
                payload={
                    "title": doc.title,
                    "doc_type": doc.doc_type.value,
                    "client": doc.client.company or doc.client.name,
                    "quality_score": doc.quality_score,
                    "flags": doc.flags[:8],
                    "total": (doc.pricing_totals or {}).get("total"),
                    "version": doc.version,
                },
                document_id=doc.id,
            )
            doc.hitl_id = action.id
            doc.status = DocStatus.pending_approval
            self.audit.write("hitl_queued", document_id=doc.id, hitl_id=action.id)
        else:
            doc.status = DocStatus.approved
            self.audit.write("auto_approved", document_id=doc.id)

        self.store.save(doc)
        self.usage.record(
            action="draft",
            tokens_in=tin,
            tokens_out=tout,
            document_id=doc.id,
        )
        self.audit.write("pipeline_complete", document_id=doc.id, status=doc.status.value)
        return doc

    def demo(self) -> Document:
        return self.draft(source="sample", doc_type="proposal")

    def approve(self, action_id: str, decided_by: str = "admin") -> Document | None:
        action = self.hitl.decide(action_id, approve=True, decided_by=decided_by)
        if not action or not action.document_id:
            return None
        doc = self.store.get(action.document_id)
        if not doc:
            return None
        doc.status = DocStatus.approved
        doc.version += 1
        doc.versions.append(
            DocVersion(
                version=doc.version,
                status=doc.status.value,
                body_markdown=doc.body_markdown,
                summary=doc.summary,
                created_by=decided_by,
                note="approved",
                export_paths=list(doc.export_paths),
            )
        )
        self.exporter.export(doc)
        self.store.save(doc)
        self.audit.write("approved", document_id=doc.id, hitl_id=action_id)
        return doc

    def reject(self, action_id: str, decided_by: str = "admin") -> Document | None:
        action = self.hitl.decide(action_id, approve=False, decided_by=decided_by)
        if not action or not action.document_id:
            return None
        doc = self.store.get(action.document_id)
        if not doc:
            return None
        doc.status = DocStatus.rejected
        self.store.save(doc)
        self.audit.write("rejected", document_id=doc.id, hitl_id=action_id)
        return doc

    def export(self, document_id: str, formats: list[str] | None = None) -> Document | None:
        doc = self.store.get(document_id)
        if not doc:
            return None
        self.exporter.export(doc, formats)
        if doc.status in {DocStatus.approved, DocStatus.exported, DocStatus.sent}:
            doc.status = DocStatus.exported
        self.store.save(doc)
        self.audit.write("exported", document_id=doc.id, formats=formats)
        self.usage.record(action="export", document_id=doc.id)
        return doc

    def send(
        self,
        document_id: str,
        recipients: list[str] | None = None,
        note: str = "",
    ) -> Document | None:
        doc = self.store.get(document_id)
        if not doc:
            return None
        if doc.status == DocStatus.pending_approval:
            self.audit.write("send_blocked_hitl", document_id=doc.id)
            return doc
        if doc.status not in {DocStatus.approved, DocStatus.exported, DocStatus.sent}:
            self.audit.write("send_blocked_status", document_id=doc.id, status=doc.status.value)
            return doc

        # Local send log (email integration stub)
        send_dir = Path(self.cfg["paths"]["data"]) / "exports" / doc.id / "send"
        send_dir.mkdir(parents=True, exist_ok=True)
        log = {
            "document_id": doc.id,
            "version": doc.version,
            "recipients": recipients or ([doc.client.email] if doc.client.email else []),
            "note": note,
            "ts": utc_now(),
            "backend": "log",
        }
        (send_dir / f"send_{utc_now().replace(':', '')[:15]}.json").write_text(
            json.dumps(log, indent=2), encoding="utf-8"
        )
        doc.send_status = "sent"
        doc.sent_at = utc_now()
        doc.sent_to = list(log["recipients"])
        doc.status = DocStatus.sent
        self.store.save(doc)
        self.audit.write("sent", document_id=doc.id, recipients=doc.sent_to)
        self.usage.record(action="send", document_id=doc.id)
        return doc

    def status(self) -> dict[str, Any]:
        docs = self.store.list(limit=200)
        pending = self.hitl.list_pending()
        return {
            "service": "doc-forge",
            "version": "1.0.0",
            "grok": grok_available(self.cfg),
            "documents": len(docs),
            "pending_approval": len(pending),
            "templates": len(self.templates.list()),
            "usage": self.usage.summary(days=30),
        }
