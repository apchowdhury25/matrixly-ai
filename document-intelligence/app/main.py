"""
Matrixly Document Intelligence API entrypoint.

Run:
  uvicorn app.main:app --reload --port 8080

Contact: anwar.chowdhury@matrixly.net · https://matrixly.net
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.config import get_settings
from app.db import dispose_engines
from app.routers import documents

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("matrixly.documents")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    logger.info(
        "starting %s env=%s site=%s support=%s",
        settings.app_name,
        settings.environment,
        settings.public_site,
        settings.support_email,
    )
    yield
    await dispose_engines()
    logger.info("shutdown complete")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description=(
            "Multi-tenant document upload, processing, and hybrid search for Matrixly agents. "
            "API and database use English identifiers only; UI locales are front-end only."
        ),
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.environment == "development" else [settings.public_site],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/healthz", tags=["ops"])
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "service": "document-intelligence", "version": __version__}

    app.include_router(documents.router, prefix=settings.api_prefix)
    return app


app = create_app()
