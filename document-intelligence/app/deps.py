"""
FastAPI dependencies: tenant extraction and session binding.

Security:
  • Always resolve tenant_id from trusted claims (JWT) or mapped API key
  • SET LOCAL app.current_tenant_id on the RLS session before any query
  • Never accept tenant_id solely from untrusted query params for writes
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db import SessionRLS, set_tenant_context
from app.schemas import TenantPrincipal

# Optional static API keys for development / SMB partners:
# Set MATRIXLY_API_KEYS as JSON in env later; for now empty (JWT preferred).
_DEV_API_KEYS: dict[str, str] = {}


def _decode_jwt(token: str, settings: Settings) -> dict:
    options = {"verify_aud": bool(settings.jwt_audience)}
    return jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
        audience=settings.jwt_audience if settings.jwt_audience else None,
        options=options,
    )


async def get_principal(
    settings: Annotated[Settings, Depends(get_settings)],
    authorization: Annotated[str | None, Header()] = None,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
    x_tenant_id: Annotated[str | None, Header(alias="X-Tenant-Id")] = None,
) -> TenantPrincipal:
    """
    Resolve tenant + subject from Bearer JWT or API key.

    JWT claims (English keys):
      tenant_id | tid  — UUID string
      sub              — user id
      roles            — optional list

    Dev-only: X-API-Key + X-Tenant-Id when jwt is not used (never in production
    without hardening the key store).
    """
    # --- Bearer JWT ---
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        try:
            claims = _decode_jwt(token, settings)
        except JWTError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            ) from exc

        raw_tid = claims.get("tenant_id") or claims.get("tid")
        if not raw_tid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing tenant_id claim",
            )
        try:
            tenant_id = UUID(str(raw_tid))
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid tenant_id in token",
            ) from exc

        roles = claims.get("roles") or []
        if isinstance(roles, str):
            roles = [roles]
        return TenantPrincipal(
            tenant_id=tenant_id,
            subject=str(claims.get("sub") or "unknown"),
            roles=list(roles),
            auth_method="jwt",
        )

    # --- API key (dev / simple) ---
    if x_api_key:
        mapped = _DEV_API_KEYS.get(x_api_key)
        if mapped:
            return TenantPrincipal(
                tenant_id=UUID(mapped),
                subject=f"api_key:{x_api_key[:6]}",
                roles=["tenant_api"],
                auth_method="api_key",
            )
        # Allow explicit tenant header only in non-production with a shared secret key
        if settings.environment == "development" and x_tenant_id:
            try:
                return TenantPrincipal(
                    tenant_id=UUID(x_tenant_id),
                    subject=f"api_key:{x_api_key[:6]}",
                    roles=["tenant_api"],
                    auth_method="api_key",
                )
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid X-Tenant-Id",
                ) from exc

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required (Bearer JWT or X-API-Key)",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_db_with_tenant(
    principal: Annotated[TenantPrincipal, Depends(get_principal)],
) -> AsyncGenerator[AsyncSession, None]:
    """
    Yield an AsyncSession with app.current_tenant_id set for RLS.
    Commits on success; rolls back on error.
    """
    async with SessionRLS() as session:
        try:
            await set_tenant_context(session, principal.tenant_id)
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# Typed aliases for routers
CurrentTenant = Annotated[TenantPrincipal, Depends(get_principal)]
DbSession = Annotated[AsyncSession, Depends(get_db_with_tenant)]
