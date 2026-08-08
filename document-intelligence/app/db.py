"""
Database engines and session factories.

Two connection paths:
  1. RLS session  — application users; must call set_tenant_context()
  2. Service session — ARQ workers / admin; BYPASSRLS role, still pass tenant_id
     explicitly in queries for defense in depth

Never expose the service DSN to browsers or untrusted agents.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import Settings, get_settings


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for ORM models."""


def _build_engine(url: str, settings: Settings) -> AsyncEngine:
    return create_async_engine(
        url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        echo=settings.db_echo,
        pool_pre_ping=True,
        # Future-proof: statement timeout can be set via connect_args / server settings
    )


_settings = get_settings()

# RLS-enforced pool (API request path)
engine_rls: AsyncEngine = _build_engine(_settings.database_url, _settings)
SessionRLS = async_sessionmaker(engine_rls, class_=AsyncSession, expire_on_commit=False)

# Service pool (workers — BYPASSRLS). Guard usage carefully.
engine_service: AsyncEngine = _build_engine(_settings.database_service_url, _settings)
SessionService = async_sessionmaker(
    engine_service, class_=AsyncSession, expire_on_commit=False
)


async def set_tenant_context(session: AsyncSession, tenant_id: UUID) -> None:
    """
    Bind this transaction to a tenant for RLS.

    Uses SET LOCAL so the GUC is transaction-scoped (safe with pooled connections).
    """
    # SET LOCAL does not support bind parameters for the value in all drivers;
    # UUID is validated before interpolation.
    tid = str(tenant_id)
    await session.execute(text(f"SET LOCAL app.current_tenant_id = '{tid}'"))


async def get_rls_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: plain RLS session (tenant set by CurrentTenant)."""
    async with SessionRLS() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_service_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Service session for workers. Does NOT set tenant GUC by default;
    DocumentService methods accept explicit tenant_id for writes under bypass.
    """
    async with SessionService() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def rls_session_for_tenant(tenant_id: UUID) -> AsyncGenerator[AsyncSession, None]:
    """Context manager used by services outside FastAPI Depends."""
    async with SessionRLS() as session:
        try:
            await set_tenant_context(session, tenant_id)
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def service_session_scope() -> AsyncGenerator[AsyncSession, None]:
    async with SessionService() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def dispose_engines() -> None:
    await engine_rls.dispose()
    await engine_service.dispose()
