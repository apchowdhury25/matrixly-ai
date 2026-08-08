"""
Pydantic v2 request/response models.

All field names and enum values are English. Front-end locales never alter these.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DocumentStatus(str, Enum):
    pending = "pending"
    queued = "queued"
    processing = "processing"
    ready = "ready"
    failed = "failed"
    deleted = "deleted"


class DocumentUploadRequest(BaseModel):
    """JSON metadata accompanying a multipart file upload (or URI-only ingest)."""

    title: str = Field(..., min_length=1, max_length=500)
    metadata: dict[str, Any] = Field(default_factory=dict)
    # Optional remote source instead of multipart body
    source_uri: str | None = Field(
        default=None,
        description="Optional s3:// or https:// URI when not uploading bytes",
    )

    @field_validator("title")
    @classmethod
    def strip_title(cls, v: str) -> str:
        return v.strip()


class DocumentProcessRequest(BaseModel):
    """Enqueue or re-run processing for a document."""

    force: bool = Field(
        default=False,
        description="Re-process even if status is ready",
    )


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000)
    limit: int = Field(default=10, ge=1, le=50)
    document_id: UUID | None = None
    vector_weight: float = Field(default=0.7, ge=0.0, le=1.0)
    fts_weight: float = Field(default=0.3, ge=0.0, le=1.0)
    min_similarity: float = Field(default=0.0, ge=0.0, le=1.0)

    @field_validator("query")
    @classmethod
    def strip_query(cls, v: str) -> str:
        return v.strip()


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    title: str
    filename: str | None = None
    content_type: str | None = None
    storage_uri: str | None = None
    byte_size: int | None = None
    status: DocumentStatus
    error_message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    chunk_count: int = 0
    page_count: int | None = None
    created_by: str | None = None
    created_at: datetime
    updated_at: datetime
    processed_at: datetime | None = None


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int


class SearchHit(BaseModel):
    chunk_id: UUID
    document_id: UUID
    chunk_index: int
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    document_title: str
    vector_score: float
    fts_score: float
    hybrid_score: float


class SearchResponse(BaseModel):
    query: str
    hits: list[SearchHit]
    count: int


class MessageResponse(BaseModel):
    message: str
    document_id: UUID | None = None
    status: DocumentStatus | None = None


class TenantPrincipal(BaseModel):
    """Authenticated caller identity (English codes)."""

    tenant_id: UUID
    subject: str  # user id or service name
    roles: list[str] = Field(default_factory=list)
    auth_method: str = "jwt"  # jwt | api_key
