"""Knowledge Retriever — search local index + optional LLM re-rank."""

from __future__ import annotations

from .. import llm
from ..config import prompt_text
from ..memory.vector_store import VectorStore
from ..models import KbHit, SupportState


def run_knowledge(state: SupportState, cfg: dict, store: VectorStore) -> SupportState:
    kb_cfg = cfg.get("knowledge") or {}
    top_k = int(kb_cfg.get("top_k") or 4)
    hits = store.search(state.text, top_k=top_k)
    state.kb_hits = [KbHit(**h) for h in hits]

    if not hits:
        state.retrieval_confidence = 0.1
        state.add_audit("knowledge_empty")
        return state

    # Base confidence from best retrieval score (TF-IDF cosine often 0.05–0.5)
    best = max(h["score"] for h in hits)
    # Map sparse cosine scores into a support-friendly 0–1 confidence band
    base = min(0.95, best * 2.4 + 0.28)

    # Topic-aligned boost when source filename matches topic
    topic = state.topic.value
    if any(
        topic in (h.get("source") or "").lower()
        or topic in (h.get("title") or "").lower()
        for h in hits
    ):
        base = min(0.95, base + 0.1)
    # Strong lexical overlap with top chunk → higher trust for FAQ auto-reply
    q_tokens = set(state.text.lower().split())
    top_tokens = set((hits[0].get("chunk") or "").lower().split())
    if q_tokens and len(q_tokens & top_tokens) >= 2:
        base = min(0.95, base + 0.08)

    if llm.grok_available(cfg) and hits:
        try:
            system = prompt_text("knowledge") or "Score retrieval confidence as JSON."
            ctx = "\n\n".join(
                f"[{i}] ({h['source']} score={h['score']})\n{h['chunk'][:500]}"
                for i, h in enumerate(hits)
            )
            user = f"Question: {state.text}\n\nChunks:\n{ctx}"
            content, tin, tout = llm.chat(cfg, system, user, temperature=0.0)
            state.usage_tokens_in += tin
            state.usage_tokens_out += tout
            data = llm.extract_json(content)
            conf = float(data.get("confidence", base))
            state.retrieval_confidence = max(0.0, min(1.0, conf))
            # Reorder by best_chunk_ids if provided
            ids = data.get("best_chunk_ids") or []
            if ids:
                ordered: list[KbHit] = []
                for i in ids:
                    try:
                        ordered.append(state.kb_hits[int(i)])
                    except Exception:
                        pass
                for h in state.kb_hits:
                    if h not in ordered:
                        ordered.append(h)
                state.kb_hits = ordered
            state.add_audit("knowledge_llm", confidence=state.retrieval_confidence)
            return state
        except Exception as e:
            state.add_audit("knowledge_llm_fallback", error=str(e))

    state.retrieval_confidence = round(base, 3)
    state.add_audit(
        "knowledge_rules",
        confidence=state.retrieval_confidence,
        hits=len(hits),
        best_score=best,
    )
    return state
