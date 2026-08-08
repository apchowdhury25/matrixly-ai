"""
ARQ tasks for document processing.

Worker uses the **service** DB role (BYPASSRLS) but still scopes every
operation by tenant_id passed in the job payload (defense in depth).
"""

from __future__ import annotations

import logging
from uuid import UUID

from app.config import get_settings
from app.db import service_session_scope, set_tenant_context
from app.services.document_service import DocumentService

logger = logging.getLogger(__name__)


async def process_document_task(ctx: dict, document_id: str, tenant_id: str) -> dict:
    """
    ARQ job entrypoint.

    Steps (placeholders for extract/embed are inside DocumentService):
      1. Open service session
      2. Optionally set tenant GUC for consistency with RLS-tested paths
      3. process_document_inline
    """
    settings = get_settings()
    doc_uuid = UUID(document_id)
    tenant_uuid = UUID(tenant_id)

    logger.info(
        "process_document_task start doc=%s tenant=%s",
        document_id,
        tenant_id,
    )

    async with service_session_scope() as session:
        # Even with BYPASSRLS, set GUC so any RLS-aware functions behave
        try:
            await set_tenant_context(session, tenant_uuid)
        except Exception:
            # Service role may not need GUC; continue with explicit filters
            logger.debug("set_tenant_context skipped/failed for service session")

        svc = DocumentService(
            session,
            tenant_id=tenant_uuid,
            settings=settings,
            use_service_role=True,
        )
        doc = await svc.process_document_inline(doc_uuid)
        return {
            "document_id": str(doc.id),
            "status": doc.status.value if hasattr(doc.status, "value") else str(doc.status),
            "chunk_count": doc.chunk_count,
        }


class WorkerSettings:
    """ARQ worker settings object (arq app.workers.tasks.WorkerSettings)."""

    functions = [process_document_task]
    redis_settings = None  # set in worker.py from env
    queue_name = "matrixly:documents"
    max_jobs = 10
    job_timeout = 600  # seconds
