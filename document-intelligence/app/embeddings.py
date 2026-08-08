"""
Embedding provider abstraction.

Swap OpenAI / local / Voyage / etc. without changing table schemas as long as
dimensions stay 1536 (or migrate to a new column for a different size).
"""

from __future__ import annotations

import hashlib
import math
import struct
from abc import ABC, abstractmethod
from typing import Sequence

from app.config import Settings, get_settings


class EmbeddingProvider(ABC):
    dimensions: int

    @abstractmethod
    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed many passages (chunk bodies)."""

    @abstractmethod
    async def embed_query(self, text: str) -> list[float]:
        """Embed a search query (may use a different instruction prefix later)."""


class PlaceholderEmbeddingProvider(EmbeddingProvider):
    """
    Deterministic pseudo-embeddings for local dev / CI without API keys.

    NOT for production quality retrieval — only shape-compatible vectors.
    """

    def __init__(self, dimensions: int = 1536) -> None:
        self.dimensions = dimensions

    def _embed_one(self, text: str) -> list[float]:
        # Hash-based unit vector so identical text → identical embedding
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        # Expand hash stream
        raw = digest
        while len(raw) < self.dimensions * 4:
            raw += hashlib.sha256(raw).digest()
        vals = list(struct.unpack(f"{self.dimensions}f", raw[: self.dimensions * 4]))
        # L2 normalize
        norm = math.sqrt(sum(v * v for v in vals)) or 1.0
        return [v / norm for v in vals]

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]

    async def embed_query(self, text: str) -> list[float]:
        return self._embed_one(text)


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI-compatible embeddings API (official or Azure / proxy)."""

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-small",
        dimensions: int = 1536,
        base_url: str | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.dimensions = dimensions
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")

    async def _call(self, texts: Sequence[str]) -> list[list[float]]:
        import httpx

        payload: dict = {"model": self.model, "input": list(texts)}
        # text-embedding-3-* supports dimensions param
        if self.model.startswith("text-embedding-3"):
            payload["dimensions"] = self.dimensions

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.base_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()["data"]
            data_sorted = sorted(data, key=lambda x: x["index"])
            return [row["embedding"] for row in data_sorted]

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        # Batch to stay under request limits
        out: list[list[float]] = []
        batch_size = 64
        for i in range(0, len(texts), batch_size):
            out.extend(await self._call(texts[i : i + batch_size]))
        return out

    async def embed_query(self, text: str) -> list[float]:
        vectors = await self._call([text])
        return vectors[0]


def get_embedding_provider(settings: Settings | None = None) -> EmbeddingProvider:
    settings = settings or get_settings()
    if settings.embedding_provider == "openai":
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY required when EMBEDDING_PROVIDER=openai")
        return OpenAIEmbeddingProvider(
            api_key=settings.openai_api_key,
            model=settings.embedding_model,
            dimensions=settings.embedding_dimensions,
            base_url=settings.openai_base_url,
        )
    return PlaceholderEmbeddingProvider(dimensions=settings.embedding_dimensions)
