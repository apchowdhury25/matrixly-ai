"""
DocumentService — multi-tenant document lifecycle + hybrid search.

All public methods expect either:
  • an RLS-bound AsyncSession (tenant GUC already set), or
  • a service session with explicit tenant_id on every write/read filter
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence
from uuid import UUID, uuid4

from sqlalchemy import delete, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.chunking import TextChunk, chunk_text, extract_text_placeholder
from app.config import Settings, get_settings
from app.embeddings import EmbeddingProvider, get_embedding_provider
from app.orm import Document, DocumentChunk
from app.schemas import (
    DocumentListResponse,
    DocumentResponse,
    DocumentStatus,
    SearchHit,
    SearchRequest,
    SearchResponse,
)

logger = logging.getLogger(__name__)


def _doc_to_response(doc: Document) -> DocumentResponse:
    return DocumentResponse(
        id=doc.id,
        tenant_id=doc.tenant_id,
        title=doc.title,
        filename=doc.filename,
        content_type=doc.content_type,
        storage_uri=doc.storage_uri,
        byte_size=doc.byte_size,
        status=DocumentStatus(doc.status),
        error_message=doc.error_message,
        metadata=dict(doc.metadata_ or {}),
        chunk_count=doc.chunk_count or 0,
        page_count=doc.page_count,
        created_by=doc.created_by,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        processed_at=doc.processed_at,
    )


class DocumentService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        tenant_id: UUID,
        settings: Settings | None = None,
        embeddings: EmbeddingProvider | None = None,
        use_service_role: bool = False,
    ) -> None:
        """
        :param session: SQLAlchemy async session
        :param tenant_id: always required (defense in depth even with RLS)
        :param use_service_role: True when session is BYPASSRLS (workers)
        """
        self.session = session
        self.tenant_id = tenant_id
        self.settings = settings or get_settings()
        self.embeddings = embeddings or get_embedding_provider(self.settings)
        self.use_service_role = use_service_role

    # ------------------------------------------------------------------
    # Upload / register
    # ------------------------------------------------------------------
    async def upload_document(
        self,
        *,
        title: str,
        filename: str | None,
        content_type: str | None,
        raw_bytes: bytes | None,
        source_uri: str | None = None,
        metadata: dict[str, Any] | None = None,
        created_by: str | None = None,
    ) -> DocumentResponse:
        if raw_bytes is None and not source_uri:
            raise ValueError("Either raw_bytes or source_uri is required")

        if raw_bytes is not None and len(raw_bytes) > self.settings.max_upload_bytes:
            raise ValueError(
                f"File exceeds max_upload_bytes ({self.settings.max_upload_bytes})"
            )

        doc_id = uuid4()
        storage_uri = source_uri
        checksum = None
        byte_size = None

        if raw_bytes is not None:
            byte_size = len(raw_bytes)
            checksum = hashlib.sha256(raw_bytes).hexdigest()
            storage_uri = await self._persist_bytes(doc_id, filename, raw_bytes)

        doc = Document(
            id=doc_id,
            tenant_id=self.tenant_id,
            title=title,
            filename=filename,
            content_type=content_type,
            storage_uri=storage_uri,
            byte_size=byte_size,
            checksum_sha256=checksum,
            status="pending",
            metadata_=metadata or {},
            created_by=created_by,
        )
        self.session.add(doc)
        await self.session.flush()
        logger.info(
            "document_uploaded tenant=%s doc=%s title=%s",
            self.tenant_id,
            doc_id,
            title,
        )
        return _doc_to_response(doc)

    async def _persist_bytes(
        self, doc_id: UUID, filename: str | None, raw: bytes
    ) -> str:
        base = Path(self.settings.document_storage_dir) / str(self.tenant_id)
        base.mkdir(parents=True, exist_ok=True)
        safe_name = (filename or "upload.bin").replace("/", "_").replace("\\", "_")
        path = base / f"{doc_id}_{safe_name}"
        path.write_bytes(raw)
        return f"file://{path.resolve()}"

    # ------------------------------------------------------------------
    # Queue processing
    # ------------------------------------------------------------------
    async def queue_processing(self, document_id: UUID, *, force: bool = False) -> DocumentResponse:
        doc = await self.get_document_orm(document_id)
        if doc is None:
            raise LookupError("Document not found")
        if doc.status == "ready" and not force:
            return _doc_to_response(doc)
        if doc.status == "deleted":
            raise ValueError("Cannot process a deleted document")

        doc.status = "queued"
        doc.error_message = None
        await self.session.flush()

        # Enqueue ARQ job (lazy import to keep API import light)
        try:
            from arq import create_pool
            from arq.connections import RedisSettings

            redis = await create_pool(RedisSettings.from_dsn(self.settings.redis_url))
            await redis.enqueue_job(
                "process_document_task",
                str(document_id),
                str(self.tenant_id),
                _queue_name=self.settings.arq_queue_name,
            )
            await redis.aclose()
        except Exception as exc:  # Redis optional in pure unit tests
            logger.warning("queue_enqueue_failed doc=%s err=%s", document_id, exc)
            # Leave status queued; worker/cron can pick up, or process inline in dev
            if self.settings.environment == "development":
                await self.process_document_inline(document_id)

        return _doc_to_response(doc)

    # ------------------------------------------------------------------
    # Inline / worker processing
    # ------------------------------------------------------------------
    async def process_document_inline(self, document_id: UUID) -> DocumentResponse:
        """
        Extract → chunk → embed → insert_chunks.
        Used by ARQ worker (service session) or dev fallback.
        """
        doc = await self.get_document_orm(document_id)
        if doc is None:
            raise LookupError("Document not found")

        doc.status = "processing"
        await self.session.flush()

        try:
            raw = self._read_storage(doc.storage_uri)
            text_body = extract_text_placeholder(doc.filename, raw, doc.content_type)
            chunks = chunk_text(
                text_body,
                chunk_size=self.settings.chunk_size_chars,
                overlap=self.settings.chunk_overlap_chars,
            )
            embeddings = await self.embeddings.embed_documents([c.content for c in chunks])
            await self.insert_chunks(document_id, chunks, embeddings)

            doc.status = "ready"
            doc.chunk_count = len(chunks)
            doc.processed_at = datetime.now(timezone.utc)
            doc.error_message = None
            await self.session.flush()
            return _doc_to_response(doc)
        except Exception as exc:
            logger.exception("process_failed doc=%s", document_id)
            doc.status = "failed"
            doc.error_message = str(exc)[:2000]
            await self.session.flush()
            raise

    def _read_storage(self, storage_uri: str | None) -> bytes | None:
        if not storage_uri:
            return None
        if storage_uri.startswith("file://"):
            path = Path(storage_uri.removeprefix("file://"))
            return path.read_bytes()
        # s3:// etc. — placeholder
        logger.warning("unsupported_storage_uri uri=%s", storage_uri)
        return None

    async def insert_chunks(
        self,
        document_id: UUID,
        chunks: Sequence[TextChunk],
        embeddings: Sequence[Sequence[float]],
    ) -> int:
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings length mismatch")

        # Replace existing chunks for re-process
        await self.session.execute(
            delete(DocumentChunk).where(
                DocumentChunk.document_id == document_id,
                DocumentChunk.tenant_id == self.tenant_id,
            )
        )

        for ch, emb in zip(chunks, embeddings):
            row = DocumentChunk(
                id=uuid4(),
                tenant_id=self.tenant_id,
                document_id=document_id,
                chunk_index=ch.index,
                content=ch.content,
                token_count=max(1, len(ch.content) // 4),
                embedding=list(emb),
                metadata_=dict(ch.metadata),
            )
            self.session.add(row)

        await self.session.execute(
            update(Document)
            .where(Document.id == document_id, Document.tenant_id == self.tenant_id)
            .values(chunk_count=len(chunks))
        )
        await self.session.flush()
        return len(chunks)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------
    async def hybrid_search(self, req: SearchRequest) -> SearchResponse:
        query_embedding = await self.embeddings.embed_query(req.query)
        # Pass vector as pgvector string literal
        emb_literal = "[" + ",".join(str(float(x)) for x in query_embedding) + "]"

        sql = text(
            """
            SELECT
              chunk_id, document_id, chunk_index, content, metadata,
              document_title, vector_score, fts_score, hybrid_score
            FROM public.search_documents_hybrid(
              :query_text,
              CAST(:embedding AS vector),
              :limit,
              :vector_weight,
              :fts_weight,
              :document_id,
              :min_similarity
            )
            """
        )
        result = await self.session.execute(
            sql,
            {
                "query_text": req.query,
                "embedding": emb_literal,
                "limit": req.limit,
                "vector_weight": req.vector_weight,
                "fts_weight": req.fts_weight,
                "document_id": str(req.document_id) if req.document_id else None,
                "min_similarity": req.min_similarity,
            },
        )
        hits: list[SearchHit] = []
        for row in result.mappings():
            meta = row["metadata"] or {}
            if not isinstance(meta, dict):
                meta = dict(meta)
            hits.append(
                SearchHit(
                    chunk_id=row["chunk_id"],
                    document_id=row["document_id"],
                    chunk_index=row["chunk_index"],
                    content=row["content"],
                    metadata=meta,
                    document_title=row["document_title"],
                    vector_score=float(row["vector_score"] or 0),
                    fts_score=float(row["fts_score"] or 0),
                    hybrid_score=float(row["hybrid_score"] or 0),
                )
            )
        return SearchResponse(query=req.query, hits=hits, count=len(hits))

    # ------------------------------------------------------------------
    # CRUD helpers
    # ------------------------------------------------------------------
    async def get_document_orm(self, document_id: UUID) -> Document | None:
        q = select(Document).where(
            Document.id == document_id,
            Document.tenant_id == self.tenant_id,
            Document.deleted_at.is_(None),
        )
        res = await self.session.execute(q)
        return res.scalar_one_or_none()

    async def get_document(self, document_id: UUID) -> DocumentResponse | None:
        doc = await self.get_document_orm(document_id)
        return _doc_to_response(doc) if doc else None

    async def list_documents(
        self, *, limit: int = 50, offset: int = 0
    ) -> DocumentListResponse:
        base = select(Document).where(
            Document.tenant_id == self.tenant_id,
            Document.deleted_at.is_(None),
            Document.status != "deleted",
        )
        count_q = select(func.count()).select_from(base.subquery())
        total = int((await self.session.execute(count_q)).scalar_one())

        q = (
            base.order_by(Document.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = (await self.session.execute(q)).scalars().all()
        return DocumentListResponse(
            items=[_doc_to_response(d) for d in rows],
            total=total,
        )

    async def soft_delete(self, document_id: UUID) -> DocumentResponse:
        doc = await self.get_document_orm(document_id)
        if doc is None:
            raise LookupError("Document not found")
        doc.status = "deleted"
        doc.deleted_at = datetime.now(timezone.utc)
        await self.session.flush()
        return _doc_to_response(doc)
