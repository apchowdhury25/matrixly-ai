"""PDF text extraction helpers.

Vision LLM extraction is preferred when XAI is available; this module
provides deterministic text pull for rule-based and hybrid paths.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional


class PdfExtractor:
    """Extract plain text from PDF files (pypdf if installed)."""

    async def extract_text(self, path: str | Path) -> str:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"PDF not found: {p}")
        if p.suffix.lower() not in {".pdf", ".txt", ".md"}:
            # Allow sample .txt “invoices” in demos
            return p.read_text(encoding="utf-8", errors="ignore")

        if p.suffix.lower() != ".pdf":
            return p.read_text(encoding="utf-8", errors="ignore")

        try:
            from pypdf import PdfReader  # type: ignore
        except ImportError as e:
            raise RuntimeError(
                "pypdf is required for PDF extraction. pip install pypdf"
            ) from e

        reader = PdfReader(str(p))
        parts: list[str] = []
        for page in reader.pages:
            try:
                parts.append(page.extract_text() or "")
            except Exception:
                continue
        text = "\n".join(parts).strip()
        if not text:
            return f"[PDF has no extractable text layer: {p.name}]"
        return text

    async def exists(self, path: str | Path) -> bool:
        return Path(path).exists()
