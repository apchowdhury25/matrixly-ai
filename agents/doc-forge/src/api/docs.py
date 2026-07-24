"""Document draft / template / export API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel

from ..models import DraftRequest, SendRequest
from ..orchestrator import DocForge
from .deps import rate_limiter, require_api_key, require_widget_or_api_key


class NoteBody(BaseModel):
    note: str


class ClauseBody(BaseModel):
    name: str
    body: str


class ExportBody(BaseModel):
    formats: list[str] = []


def build_docs_router(agent: DocForge, cfg: dict) -> APIRouter:
    router = APIRouter(prefix="/v1", tags=["documents"])
    admin = require_api_key(cfg)
    widget = require_widget_or_api_key(cfg)
    limit = int((cfg.get("rate_limit") or {}).get("draft_per_minute") or 20)

    @router.post("/draft")
    async def draft(body: DraftRequest, request: Request, _: None = Depends(widget)):
        rate_limiter.check(f"df:{request.client.host if request.client else 'x'}", limit)
        doc = agent.draft(
            doc_type=body.doc_type,
            client=body.client,
            project=body.project,
            line_items=body.line_items,
            discount_pct=body.discount_pct,
            notes=body.notes,
            template_id=body.template_id,
            source=body.source,
            crm_account=body.crm_account,
            metadata=body.metadata,
        )
        return doc.model_dump()

    @router.post("/demo")
    async def demo(_: None = Depends(widget)):
        return agent.demo().model_dump()

    @router.get("/documents")
    async def list_docs(status: str | None = None, _: None = Depends(admin)):
        return {"items": [d.model_dump() for d in agent.store.list(status=status)]}

    @router.get("/documents/{document_id}")
    async def get_doc(document_id: str, _: None = Depends(admin)):
        doc = agent.store.get(document_id)
        if not doc:
            raise HTTPException(404, "Document not found")
        return doc.model_dump()

    @router.get("/documents/{document_id}/versions")
    async def versions(document_id: str, _: None = Depends(admin)):
        return {"items": agent.store.list_versions(document_id)}

    @router.post("/documents/{document_id}/export")
    async def export(document_id: str, body: ExportBody | None = None, _: None = Depends(admin)):
        body = body or ExportBody()
        doc = agent.export(document_id, body.formats or None)
        if not doc:
            raise HTTPException(404, "Document not found")
        return doc.model_dump()

    @router.post("/documents/{document_id}/send")
    async def send(document_id: str, body: SendRequest | None = None, _: None = Depends(admin)):
        body = body or SendRequest(document_id=document_id)
        doc = agent.send(document_id, recipients=body.recipients, note=body.note)
        if not doc:
            raise HTTPException(404, "Document not found")
        return doc.model_dump()

    @router.get("/templates")
    async def templates(_: None = Depends(admin)):
        return {"items": agent.templates.list()}

    @router.post("/templates/{template_id}")
    async def upload_template(
        template_id: str,
        content: str = Form(""),
        file: UploadFile | None = File(None),
        _: None = Depends(admin),
    ):
        text = content
        if file is not None:
            text = (await file.read()).decode("utf-8", errors="ignore")
        if not text.strip():
            raise HTTPException(400, "template content required")
        path = agent.templates.save(template_id, text)
        agent.audit.write("template_saved", template_id=template_id, path=str(path))
        return {"ok": True, "id": template_id, "path": str(path)}

    @router.get("/brand")
    async def brand(_: None = Depends(admin)):
        return {
            "guidelines_preview": agent.brand.guidelines()[:2500],
            "notes": agent.brand.notes(),
            "clauses": agent.brand.clauses(),
        }

    @router.post("/brand/notes")
    async def brand_note(body: NoteBody, _: None = Depends(admin)):
        if not body.note.strip():
            raise HTTPException(400, "note required")
        return agent.brand.add_note(body.note)

    @router.post("/brand/clauses")
    async def brand_clause(body: ClauseBody, _: None = Depends(admin)):
        if not body.name.strip() or not body.body.strip():
            raise HTTPException(400, "name and body required")
        return agent.brand.add_clause(body.name, body.body)

    return router
