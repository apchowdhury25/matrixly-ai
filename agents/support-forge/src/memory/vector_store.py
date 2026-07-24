"""Lightweight local knowledge index (TF-IDF style, no heavy ML deps)."""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any


_TOKEN = re.compile(r"[a-z0-9]{2,}", re.I)


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN.findall(text or "")]


def chunk_text(text: str, size: int = 600, overlap: int = 80) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]
    chunks: list[str] = []
    i = 0
    while i < len(text):
        chunks.append(text[i : i + size])
        i += max(1, size - overlap)
    return chunks


class VectorStore:
    def __init__(self, data_dir: str | Path) -> None:
        self.dir = Path(data_dir) / "vector"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.dir / "index.json"
        self._docs: list[dict[str, Any]] = []
        self._df: Counter[str] = Counter()
        self._n = 0
        self.load()

    def load(self) -> None:
        if not self.index_path.exists():
            self._docs = []
            self._df = Counter()
            self._n = 0
            return
        with self.index_path.open(encoding="utf-8") as f:
            raw = json.load(f)
        self._docs = raw.get("docs") or []
        self._df = Counter(raw.get("df") or {})
        self._n = int(raw.get("n") or len(self._docs))

    def save(self) -> None:
        payload = {
            "docs": self._docs,
            "df": dict(self._df),
            "n": self._n,
        }
        with self.index_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    def clear(self) -> None:
        self._docs = []
        self._df = Counter()
        self._n = 0
        self.save()

    def add_document(
        self,
        text: str,
        source: str,
        title: str = "",
        chunk_size: int = 600,
        overlap: int = 80,
    ) -> int:
        added = 0
        for i, ch in enumerate(chunk_text(text, chunk_size, overlap)):
            toks = tokenize(ch)
            if not toks:
                continue
            tf = Counter(toks)
            self._docs.append(
                {
                    "id": len(self._docs),
                    "text": ch,
                    "source": source,
                    "title": title or Path(source).stem,
                    "tf": dict(tf),
                    "len": len(toks),
                }
            )
            for t in set(toks):
                self._df[t] += 1
            added += 1
        self._n = len(self._docs)
        return added

    def index_directory(
        self,
        knowledge_dir: str | Path,
        chunk_size: int = 600,
        overlap: int = 80,
    ) -> dict[str, Any]:
        knowledge_dir = Path(knowledge_dir)
        self.clear()
        files = 0
        chunks = 0
        if knowledge_dir.exists():
            for path in sorted(knowledge_dir.rglob("*")):
                if path.suffix.lower() not in {".md", ".txt", ".markdown"}:
                    continue
                text = path.read_text(encoding="utf-8", errors="ignore")
                files += 1
                chunks += self.add_document(
                    text,
                    source=str(path.relative_to(knowledge_dir)),
                    title=path.stem,
                    chunk_size=chunk_size,
                    overlap=overlap,
                )
        self.save()
        return {"files": files, "chunks": chunks}

    def _idf(self, term: str) -> float:
        df = self._df.get(term, 0)
        if df <= 0 or self._n <= 0:
            return 0.0
        return math.log(1 + self._n / df)

    def _vec(self, tf: dict[str, int] | Counter[str]) -> dict[str, float]:
        return {t: c * self._idf(t) for t, c in tf.items()}

    @staticmethod
    def _cos(a: dict[str, float], b: dict[str, float]) -> float:
        if not a or not b:
            return 0.0
        keys = set(a) & set(b)
        if not keys:
            return 0.0
        dot = sum(a[k] * b[k] for k in keys)
        na = math.sqrt(sum(v * v for v in a.values()))
        nb = math.sqrt(sum(v * v for v in b.values()))
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)

    def search(self, query: str, top_k: int = 4) -> list[dict[str, Any]]:
        if not self._docs:
            self.load()
        q_tf = Counter(tokenize(query))
        if not q_tf:
            return []
        qv = self._vec(q_tf)
        scored: list[tuple[float, dict[str, Any]]] = []
        for doc in self._docs:
            score = self._cos(qv, self._vec(doc.get("tf") or {}))
            if score > 0:
                scored.append((score, doc))
        scored.sort(key=lambda x: x[0], reverse=True)
        out: list[dict[str, Any]] = []
        for score, doc in scored[:top_k]:
            out.append(
                {
                    "chunk": doc["text"],
                    "source": doc["source"],
                    "title": doc.get("title") or "",
                    "score": round(float(score), 4),
                }
            )
        return out

    def stats(self) -> dict[str, Any]:
        return {"documents": self._n, "terms": len(self._df), "path": str(self.index_path)}
