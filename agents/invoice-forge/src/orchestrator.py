"""LangGraph-style multi-agent orchestrator for InvoiceForge."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .agents.extract import run_extract
from .agents.post import run_post
from .agents.report import generate_report, report_markdown
from .agents.validate import run_validate
from .integrations.accounting import AccountingPoster
from .integrations.inbox import fetch_imap_invoice_bodies, list_upload_files, read_text_file
from .llm import cost_usd
from .models import (
    Invoice,
    InvoiceStatus,
    PipelineState,
    ProcessResult,
    SourceChannel,
    new_id,
)
from .services.audit import AuditLog
from .services.hitl import HitlQueue
from .services.reminders import ReminderService
from .services.store import InvoiceStore
from .services.usage import UsageMeter


class InvoiceForge:
    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg
        data = Path(cfg["paths"]["data"])
        self.store = InvoiceStore(data)
        self.hitl = HitlQueue(data)
        self.reminders = ReminderService(data, cfg)
        self.audit = AuditLog(data)
        self.usage = UsageMeter(data, cfg)
        self.poster = AccountingPoster(cfg)
        self.uploads = Path(cfg["paths"]["uploads"])
        self.samples = Path(cfg["paths"]["samples"])

    def process_text(
        self,
        text: str,
        *,
        filename: str = "invoice.txt",
        source: SourceChannel | str = SourceChannel.upload,
        source_email: str | None = None,
        image_path: str | None = None,
        notes: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> ProcessResult:
        if isinstance(source, str):
            source = SourceChannel(source)

        invoice = Invoice(
            id=new_id("inv_"),
            status=InvoiceStatus.received,
            source=source,
            source_file=filename,
            source_email=source_email,
            raw_text=text,
            notes=notes,
            metadata=metadata or {},
        )
        state = PipelineState(
            invoice_id=invoice.id,
            channel=source,
            text=text,
            image_path=image_path,
            filename=filename,
            source_email=source_email,
            metadata=metadata or {},
        )
        self.store.save(invoice)
        state.add_audit("received", filename=filename, source=source.value)

        # 1) Extract
        state, invoice = run_extract(state, self.cfg, invoice)
        self.store.save(invoice)

        # 2) Validate
        state, invoice = run_validate(state, self.cfg, invoice, self.store)
        self.store.save(invoice)

        # 3) HITL queue if needed
        if state.requires_human and invoice.status in {
            InvoiceStatus.pending_hitl,
            InvoiceStatus.exception,
        }:
            action = self.hitl.enqueue(
                kind="invoice_review",
                payload={
                    "exceptions": invoice.exceptions,
                    "validation_errors": invoice.validation_errors,
                    "vendor": invoice.vendor_name,
                    "total": invoice.total,
                    "invoice_number": invoice.invoice_number,
                },
                invoice_id=invoice.id,
            )
            invoice.hitl_id = action.id
            state.hitl_id = action.id
            self.store.save(invoice)
            state.add_audit("hitl_queued", hitl_id=action.id)
        else:
            # 4) Post when validated
            state, invoice = run_post(state, invoice, self.poster, self.reminders)
            self.store.save(invoice)

        state.estimated_cost_usd = round(
            cost_usd(self.cfg, state.usage_tokens_in, state.usage_tokens_out), 6
        )
        self.usage.record(
            action="process",
            tokens_in=state.usage_tokens_in,
            tokens_out=state.usage_tokens_out,
            invoice_id=invoice.id,
            channel=source.value,
        )
        for ev in state.audit_events:
            self.audit.write(
                ev.get("event", "pipeline"),
                invoice_id=invoice.id,
                **{k: v for k, v in ev.items() if k not in {"event", "ts"}},
            )
        self.audit.write(
            "pipeline_complete",
            invoice_id=invoice.id,
            status=invoice.status.value,
            confidence=invoice.confidence,
        )

        return ProcessResult(
            invoice=invoice,
            message=state.message,
            requires_human=state.requires_human,
            usage={
                "tokens_in": state.usage_tokens_in,
                "tokens_out": state.usage_tokens_out,
                "estimated_cost_usd": state.estimated_cost_usd,
            },
        )

    def process_file(self, path: str | Path, source: SourceChannel = SourceChannel.watch) -> ProcessResult:
        path = Path(path)
        text = ""
        image_path = None
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
            image_path = str(path)
            text = f"[image attachment: {path.name}]"
        else:
            text = read_text_file(path)
        return self.process_text(
            text,
            filename=path.name,
            source=source,
            image_path=image_path,
        )

    def watch_uploads(self) -> list[ProcessResult]:
        results: list[ProcessResult] = []
        for path in list_upload_files(self.uploads):
            # skip already processed by name marker
            marker = self.uploads / f".processed_{path.name}"
            if marker.exists():
                continue
            res = self.process_file(path, source=SourceChannel.watch)
            results.append(res)
            marker.write_text(res.invoice.id, encoding="utf-8")
        return results

    def watch_email(self) -> list[ProcessResult]:
        results: list[ProcessResult] = []
        for msg in fetch_imap_invoice_bodies(self.cfg):
            text = msg.get("body") or ""
            if msg.get("subject"):
                text = f"Subject: {msg['subject']}\n\n{text}"
            res = self.process_text(
                text,
                filename=msg.get("filename") or "email.txt",
                source=SourceChannel.email,
                source_email=msg.get("from_email"),
            )
            results.append(res)
        return results

    def approve_hitl(self, action_id: str, decided_by: str = "admin") -> Invoice | None:
        action = self.hitl.decide(action_id, approve=True, decided_by=decided_by)
        if not action or not action.invoice_id:
            return None
        invoice = self.store.get(action.invoice_id)
        if not invoice:
            return None
        invoice.status = InvoiceStatus.validated
        invoice.exceptions = [e for e in invoice.exceptions if not e.startswith("keyword:")]
        state = PipelineState(invoice_id=invoice.id, channel=invoice.source)
        state, invoice = run_post(state, invoice, self.poster, self.reminders)
        self.store.save(invoice)
        self.audit.write("hitl_approved_posted", invoice_id=invoice.id, action_id=action_id)
        return invoice

    def reject_hitl(self, action_id: str, decided_by: str = "admin") -> Invoice | None:
        action = self.hitl.decide(action_id, approve=False, decided_by=decided_by)
        if not action or not action.invoice_id:
            return None
        invoice = self.store.get(action.invoice_id)
        if not invoice:
            return None
        invoice.status = InvoiceStatus.void
        invoice.ar_status = "written_off"
        self.store.save(invoice)
        self.audit.write("hitl_rejected", invoice_id=invoice.id, action_id=action_id)
        return invoice

    def process_reminders(self) -> int:
        due = self.reminders.due()
        for item in due:
            inv = self.store.get(item.get("invoice_id") or "")
            if inv:
                inv.reminders_sent.append(item["id"])
                inv.ar_status = "reminded"
                self.store.save(inv)
            self.reminders.mark_sent(item["id"])
            self.audit.write(
                "reminder_sent",
                reminder_id=item["id"],
                invoice_id=item.get("invoice_id"),
            )
            self.usage.record(action="reminder", invoice_id=item.get("invoice_id") or "")
        return len(due)

    def report(self) -> dict[str, Any]:
        summary = generate_report(self.store, self.cfg)
        return {
            "summary": summary.model_dump(),
            "markdown": report_markdown(summary),
        }

    def demo(self) -> list[ProcessResult]:
        results: list[ProcessResult] = []
        for name in ("invoice_acme.txt", "invoice_exception.txt"):
            path = self.samples / name
            if path.exists():
                results.append(
                    self.process_text(
                        path.read_text(encoding="utf-8"),
                        filename=name,
                        source=SourceChannel.api,
                    )
                )
        return results

    def status(self) -> dict[str, Any]:
        from . import llm as llm_mod

        report = generate_report(self.store, self.cfg)
        return {
            "version": "1.0.0",
            "business": (self.cfg.get("business") or {}).get("name"),
            "accounting_backend": self.poster.backend,
            "grok": llm_mod.grok_available(self.cfg),
            "invoices": report.total_invoices,
            "exceptions": report.exceptions,
            "posted": report.posted,
            "open_ar_total": report.open_ar_total,
            "pending_hitl": len(self.hitl.list_pending()),
            "usage": self.usage.summary(days=7),
        }
