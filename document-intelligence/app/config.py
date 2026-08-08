"""
Application configuration.

All settings are English-key env vars. UI locales (en/es/fr/ar/bn/de/ms) are
front-end only and never change DB schemas, status codes, or API paths.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- App ---
    app_name: str = "Matrixly Document Intelligence"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    api_prefix: str = "/api/v1"

    # --- Database (asyncpg) ---
    # Normal pool: connects as a role subject to RLS (e.g. authenticated or app user)
    database_url: str = Field(
        default="postgresql+asyncpg://matrixly_app:matrixly@localhost:5432/matrixly",
        description="SQLAlchemy async URL for RLS-enforced sessions",
    )
    # Service pool: matrixly_service (BYPASSRLS) — workers / trusted jobs ONLY
    database_service_url: str = Field(
        default="postgresql+asyncpg://matrixly_service:matrixly_service@localhost:5432/matrixly",
        description="SQLAlchemy async URL for service role (BYPASSRLS)",
    )
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_echo: bool = False

    # --- Auth (JWT or static API keys for SMB tenants) ---
    jwt_secret: str = Field(default="change-me-in-production", min_length=8)
    jwt_algorithm: str = "HS256"
    jwt_audience: str | None = "matrixly-api"
    # Optional map of api_key -> tenant_id (dev / simple SMB keys)
    # Prefer real IdP JWT with claims: tenant_id, sub, roles
    api_key_header: str = "X-API-Key"

    # --- Storage ---
    document_storage_dir: str = "./data/uploads"
    max_upload_bytes: int = 25 * 1024 * 1024  # 25 MiB

    # --- Embeddings (swap provider without schema change if dim stays 1536) ---
    embedding_provider: Literal["openai", "placeholder"] = "placeholder"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    openai_api_key: str | None = None
    openai_base_url: str | None = None

    # --- Chunking defaults ---
    chunk_size_chars: int = 1200
    chunk_overlap_chars: int = 150

    # --- Redis / ARQ ---
    redis_url: str = "redis://localhost:6379/0"
    arq_queue_name: str = "matrixly:documents"

    # --- Contact (product ops — matrixly.net) ---
    support_email: str = "anwar.chowdhury@matrixly.net"
    public_site: str = "https://matrixly.net"

    @field_validator("database_url", "database_service_url")
    @classmethod
    def must_be_asyncpg(cls, v: str) -> str:
        if not v.startswith("postgresql+asyncpg://"):
            raise ValueError("Database URL must use postgresql+asyncpg://")
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
