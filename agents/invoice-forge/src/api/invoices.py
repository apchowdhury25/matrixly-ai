"""Invoice upload, process, and query endpoints."""

from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel

from ..models import EmailIngest, SourceChannel
from ..orchestrator import InvoiceForge
from .deps import rate_limiter, require_api_key, require_widget_or_api_key


class TextProcessBody(BaseModel):
    text: str
    filename: str = "invoice.txt"
    notes: str = ""
    source_email: str | None = None


def build_invoices_router(agent: InvoiceForge, cfg: dict) -> APIRouter:
    router = APIRouter(prefix="/v1", tags=["invoices"])
    admin_auth = require_api_key(cfg)
    upload_auth = require_widget_or_api_key(cfg)
    limit = int((cfg.get("rate_limit") or {}).get("upload_per_minute") or 30)

    @router.post("/invoices/process-text")
    async def process_text(
        body: TextProcessBody,
        request: Request,
        _: None = Depends(upload_auth),
    ):
        rate_limiter.check(f"up:{request.client.host if request.client else 'x'}", limit)
        res = agent.process_text(
            body.text,
            filename=body.filename,
            source=SourceChannel.api,
            source_email=body.source_email,
            notes=body.notes,
        )
        return {
            "message": res.message,
            "requires_human": res.requires_human,
            "invoice": res.invoice.model_dump(),
            "usage": res.usage,
        }

    @router.post("/invoices/upload")
    async def upload(
        request: Request,
        file: UploadFile = File(...),
        notes: str = Form(""),
        _: None = Depends(upload_auth),
    ):
        rate_limiter.check(f"up:{request.client.host if request.client else 'x'}", limit)
        uploads = Path(cfg["paths"]["uploads"])
        uploads.mkdir(parents=True, exist_ok=True)
        safe = Path(file.filename or "upload.bin").name
        dest = uploads / f"{Path(safe).stem}_{Path(safe).suffix}"
        # unique
        dest = uploads / safe
        i = 0
        while dest.exists():
            i += 1
            dest = uploads / f"{Path(safe).stem}_{i}{Path(safe).suffix}"
        with dest.open("wb") as f:
            shutil.copyfileobj(file.file, f)

        res = agent.process_file(dest, source=SourceChannel.upload)
        if notes:
            inv = res.invoice
            inv.notes = (inv.notes + " " + notes).strip()
            agent.store.save(inv)
            res.invoice = inv
        return {
            "message": res.message,
            "requires_human": res.requires_human,
            "invoice": res.invoice.model_dump(),
            "usage": res.usage,
            "saved_as": dest.name,
        }

    @router.get("/invoices")
    async def list_invoices(status: str | None = None, _: None = Depends(admin_auth)):
        items = agent.store.list(status=status, limit=100)
        return {"items": [i.model_dump() for i in items]}

    @router.get("/invoices/exceptions")
    async def exceptions(_: None = Depends(admin_auth)):
        items = agent.store.list_exceptions()
        return {"items": [i.model_dump() for i in items]}

    @router.get("/invoices/{invoice_id}")
    async def detail(invoice_id: str, _: None = Depends(admin_auth)):
        inv = agent.store.get(invoice_id)
        if not inv:
            raise HTTPException(404, "Invoice not found")
        return inv.model_dump()

    @router.post("/webhooks/email")
    async def email_hook(body: EmailIngest, _: None = Depends(admin_auth)):
        text = body.attachment_text or body.body
        if body.subject:
            text = f"Subject: {body.subject}\nFrom: {body.from_name or ''} <{body.from_email}>\n\n{text}"
        res = agent.process_text(
            text,
            filename=body.attachment_filename or "email_invoice.txt",
            source=SourceChannel.email,
            source_email=body.from_email,
        )
        return {
            "ok": True,
            "invoice": res.invoice.model_dump(),
            "message": res.message,
            "requires_human": res.requires_human,
        }

    @router.post("/watch/uploads")
    async def watch_uploads(_: None = Depends(admin_auth)):
        results = agent.watch_uploads()
        return {
            "processed": len(results),
            "items": [
                {"id": r.invoice.id, "status": r.invoice.status.value, "message": r.message}
                for r in results
            ],
        }

    @router.post("/watch/email")
    async def watch_email(_: None = Depends(admin_auth)):
        results = agent.watch_email()
        return {
            "processed": len(results),
            "items": [
                {"id": r.invoice.id, "status": r.invoice.status.value, "message": r.message}
                for r in results
            ],
        }

    return router
