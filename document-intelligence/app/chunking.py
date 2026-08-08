"""
Text chunking helpers (English implementation notes; content may be any language).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    index: int
    content: str
    metadata: dict


def chunk_text(
    text: str,
    *,
    chunk_size: int = 1200,
    overlap: int = 150,
) -> list[TextChunk]:
    """
    Simple character-window chunker with overlap.

    Production systems may swap in recursive / semantic / layout-aware chunkers
    without changing the DocumentService insert path.
    """
    text = (text or "").strip()
    if not text:
        return []

    if overlap >= chunk_size:
        overlap = max(0, chunk_size // 5)

    chunks: list[TextChunk] = []
    start = 0
    idx = 0
    n = len(text)
    while start < n:
        end = min(start + chunk_size, n)
        # Prefer break on paragraph/sentence boundary when possible
        if end < n:
            window = text[start:end]
            for sep in ("\n\n", "\n", ". ", " "):
                pos = window.rfind(sep)
                if pos > chunk_size * 0.5:
                    end = start + pos + len(sep)
                    break
        piece = text[start:end].strip()
        if piece:
            chunks.append(
                TextChunk(
                    index=idx,
                    content=piece,
                    metadata={"char_start": start, "char_end": end},
                )
            )
            idx += 1
        if end >= n:
            break
        start = max(end - overlap, start + 1)
    return chunks


def extract_text_placeholder(filename: str | None, raw_bytes: bytes | None, content_type: str | None) -> str:
    """
    Placeholder extractors — replace with pypdf / python-docx / unstructured later.
    """
    if raw_bytes is None:
        return ""
    # Treat as UTF-8 text when possible
    if content_type and (
        content_type.startswith("text/")
        or content_type in ("application/json", "application/xml")
    ):
        return raw_bytes.decode("utf-8", errors="replace")
    if filename and filename.lower().endswith((".txt", ".md", ".csv", ".json", ".log")):
        return raw_bytes.decode("utf-8", errors="replace")
    # Binary: return a short notice so pipeline still runs in dev
    return (
        f"[binary-placeholder] filename={filename or 'unknown'} "
        f"content_type={content_type or 'application/octet-stream'} "
        f"bytes={len(raw_bytes)}. "
        "Wire a real extractor for PDF/DOCX in production."
    )
