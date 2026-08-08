"""
Example: how a Matrixly agent tool calls hybrid document search.

This is not imported by the API — it is a reference for agent authors.
All API contracts and metadata keys are English.
"""

from __future__ import annotations

import os
from typing import Any
from uuid import UUID

import httpx

API_BASE = os.getenv("MATRIXLY_DOC_API", "http://localhost:8080/api/v1")


async def search_tenant_documents(
    *,
    bearer_token: str,
    query: str,
    limit: int = 8,
    document_id: UUID | None = None,
) -> list[dict[str, Any]]:
    """
    Agent tool surface: semantic + keyword search over the tenant's library.

    Returns list of {document_title, content, score, document_id, chunk_id}.
    """
    payload: dict[str, Any] = {
        "query": query,
        "limit": limit,
        "vector_weight": 0.7,
        "fts_weight": 0.3,
    }
    if document_id:
        payload["document_id"] = str(document_id)

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{API_BASE}/documents/search",
            headers={
                "Authorization": f"Bearer {bearer_token}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

    return [
        {
            "document_id": hit["document_id"],
            "document_title": hit["document_title"],
            "chunk_id": hit["chunk_id"],
            "content": hit["content"],
            "score": hit["hybrid_score"],
            "metadata": hit.get("metadata") or {},
        }
        for hit in data.get("hits", [])
    ]


# Optional OpenAI-style tool schema (English names/descriptions for the model)
AGENT_TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "search_documents",
        "description": (
            "Search the tenant's uploaded documents (contracts, SOPs, invoices, "
            "manuals, proposals) using hybrid semantic and keyword retrieval."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language or keyword query in any language.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max chunks to return (1-50).",
                    "default": 8,
                },
            },
            "required": ["query"],
        },
    },
}


if __name__ == "__main__":
    import asyncio

    async def _demo() -> None:
        token = os.getenv("MATRIXLY_JWT", "")
        if not token:
            print("Set MATRIXLY_JWT to a tenant JWT and re-run.")
            return
        hits = await search_tenant_documents(
            bearer_token=token,
            query="payment terms net 30",
        )
        for h in hits:
            print(f"- {h['score']:.3f} | {h['document_title']}: {h['content'][:120]}...")

    asyncio.run(_demo())
