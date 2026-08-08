"""
Document Intelligence HTTP API.

All routes require authentication; tenant isolation via RLS session GUC.
Paths and status codes are English-only (front-end locales do not affect API).
"""

from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)

from app.deps import CurrentTenant, DbSession
from app.schemas import (
    DocumentListResponse,
    DocumentProcessRequest,
    DocumentResponse,
    MessageResponse,
    SearchRequest,
    SearchResponse,
)
from app.services.document_service import DocumentService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


def _svc(session: DbSession, principal: CurrentTenant) -> DocumentService:
    return DocumentService(session, tenant_id=principal.tenant_id)


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload or register a document",
)
async def upload_document(
    principal: CurrentTenant,
    session: DbSession,
    title: Annotated[str, Form()],
    file: Annotated[UploadFile | None, File()] = None,
    source_uri: Annotated[str | None, Form()] = None,
    metadata_json: Annotated[str | None, Form()] = None,
) -> DocumentResponse:
    """
    Multipart upload: `title` + optional `file` and/or `source_uri`.
    `metadata_json` is optional JSON object string.
    """
    import json

    meta: dict = {}
    if metadata_json:
        try:
            meta = json.loads(metadata_json)
            if not isinstance(meta, dict):
                raise ValueError("metadata must be an object")
        except (json.JSONDecodeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=f"Invalid metadata_json: {exc}") from exc

    raw: bytes | None = None
    filename = None
    content_type = None
    if file is not None:
        raw = await file.read()
        filename = file.filename
        content_type = file.content_type

    svc = _svc(session, principal)
    try:
        return await svc.upload_document(
            title=title,
            filename=filename,
            content_type=content_type,
            raw_bytes=raw,
            source_uri=source_uri,
            metadata=meta,
            created_by=principal.subject,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/{document_id}/process",
    response_model=MessageResponse,
    summary="Queue document for chunking + embedding",
)
async def process_document(
    document_id: UUID,
    principal: CurrentTenant,
    session: DbSession,
    body: DocumentProcessRequest | None = None,
) -> MessageResponse:
    body = body or DocumentProcessRequest()
    svc = _svc(session, principal)
    try:
        doc = await svc.queue_processing(document_id, force=body.force)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return MessageResponse(
        message="Processing queued",
        document_id=doc.id,
        status=doc.status,
    )


@router.post(
    "/search",
    response_model=SearchResponse,
    summary="Hybrid semantic + full-text search",
)
async def search_documents(
    body: SearchRequest,
    principal: CurrentTenant,
    session: DbSession,
) -> SearchResponse:
    """Primary entry for agent tools and SMB apps."""
    svc = _svc(session, principal)
    return await svc.hybrid_search(body)


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List tenant documents",
)
async def list_documents(
    principal: CurrentTenant,
    session: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> DocumentListResponse:
    svc = _svc(session, principal)
    return await svc.list_documents(limit=limit, offset=offset)


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get one document",
)
async def get_document(
    document_id: UUID,
    principal: CurrentTenant,
    session: DbSession,
) -> DocumentResponse:
    svc = _svc(session, principal)
    doc = await svc.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.delete(
    "/{document_id}",
    response_model=MessageResponse,
    summary="Soft-delete a document",
)
async def delete_document(
    document_id: UUID,
    principal: CurrentTenant,
    session: DbSession,
) -> MessageResponse:
    svc = _svc(session, principal)
    try:
        doc = await svc.soft_delete(document_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return MessageResponse(
        message="Document deleted",
        document_id=doc.id,
        status=doc.status,
    )
