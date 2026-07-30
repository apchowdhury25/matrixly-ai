"""Optional FastAPI surface for Invoice Processor (HITL / health)."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .deps import InvoiceProcessorDeps
from .models import InvoiceInput, InvoiceProcessingResult, SourceType
from .pipeline import process_invoice

deps = InvoiceProcessorDeps.create()

app = FastAPI(
    title="Matrixly Invoice Processor",
    description="Pydantic AI multi-agent AP: extract → match PO → review (HITL)",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProcessBody(BaseModel):
    text: Optional[str] = None
    pdf_path: Optional[str] = None
    email_message_id: Optional[str] = None
    filename: Optional[str] = None
    use_llm: Optional[bool] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


@app.get("/v1/health")
async def health() -> dict[str, Any]:
    return {
        "ok": True,
        "service": "invoice-processor",
        "version": "1.0.0",
        "model": deps.model_name,
        "llm_ready": deps.model_available(),
        "pos": len(deps.po_store.list_all()),
    }


@app.get("/v1/pos")
async def list_pos() -> dict[str, Any]:
    return {"items": [p.model_dump() for p in deps.po_store.list_all()]}


@app.post("/v1/process", response_model=InvoiceProcessingResult)
async def process(body: ProcessBody) -> InvoiceProcessingResult:
    if not (body.text or body.pdf_path or body.email_message_id):
        raise HTTPException(400, "Provide text, pdf_path, or email_message_id")
    payload = InvoiceInput(
        text=body.text,
        pdf_path=body.pdf_path,
        email_message_id=body.email_message_id,
        filename=body.filename,
        source_type=(
            SourceType.pdf
            if body.pdf_path
            else SourceType.email
            if body.email_message_id
            else SourceType.text
        ),
        metadata=body.metadata,
    )
    return await process_invoice(deps, payload, use_llm=body.use_llm)


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "service": "invoice-processor",
        "docs": "/docs",
        "health": "/v1/health",
        "process": "POST /v1/process",
    }
