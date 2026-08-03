"""Parallel graph executor with isolation for verifier nodes."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from ..models import GraphNodeResult, NodeStatus, utc_now
from .nodes.handlers import run_node
from .topology import EDGES, NODES, NodeSpec, topological_waves


class GraphExecutor:
    """
    Executes the 20-node SEO-Bespoke graph in parallel waves.

    Isolation rules:
    - Each node receives only its declared inputs (plus always-safe keys).
    - Verifier nodes (N9, N18) never receive chat_history or prior node chatter.
    - Parallel groups within a wave run via ThreadPoolExecutor.
    """

    ALWAYS_KEYS = frozenset({"run_id"})

    def __init__(self, cfg: dict[str, Any], max_workers: int = 6) -> None:
        self.cfg = cfg
        self.max_workers = max_workers
        self.specs: dict[str, NodeSpec] = {n.id: n for n in NODES}
        self.waves = topological_waves()

    def _isolated_ctx(self, spec: NodeSpec, bag: dict[str, Any]) -> dict[str, Any]:
        allowed = set(spec.inputs) | self.ALWAYS_KEYS
        if spec.is_verifier:
            # Hard isolation: no chat, no intermediate debug dumps
            banned = {"chat_history", "messages", "conversation", "raw_llm_trace"}
            return {k: v for k, v in bag.items() if k in allowed and k not in banned}
        return {k: v for k, v in bag.items() if k in allowed}

    def _run_one(
        self,
        node_id: str,
        bag: dict[str, Any],
    ) -> tuple[str, GraphNodeResult, dict[str, Any]]:
        spec = self.specs[node_id]
        ctx = self._isolated_ctx(spec, bag)
        started = time.perf_counter()
        result = GraphNodeResult(
            node_id=node_id,
            name=spec.name,
            status=NodeStatus.running,
            inputs_keys=sorted(ctx.keys()),
            isolation=spec.isolation,
            started_at=utc_now(),
        )
        try:
            out = run_node(node_id, ctx, self.cfg)
            if not isinstance(out, dict):
                raise TypeError(f"{node_id} must return dict, got {type(out)}")
            # Validate declared outputs exist (soft — fill missing with empty)
            for key in spec.outputs:
                if key not in out:
                    out[key] = {}
            elapsed = int((time.perf_counter() - started) * 1000)
            result.status = NodeStatus.completed
            result.output = {k: _summarize(out.get(k)) for k in spec.outputs}
            result.finished_at = utc_now()
            result.duration_ms = elapsed
            return node_id, result, out
        except Exception as exc:  # noqa: BLE001
            elapsed = int((time.perf_counter() - started) * 1000)
            result.status = NodeStatus.failed
            result.error = str(exc)
            result.finished_at = utc_now()
            result.duration_ms = elapsed
            return node_id, result, {}

    def execute(self, initial: dict[str, Any]) -> tuple[dict[str, Any], list[GraphNodeResult]]:
        bag: dict[str, Any] = dict(initial)
        results: list[GraphNodeResult] = []
        failed = False

        for wave in self.waves:
            if failed:
                for nid in wave:
                    results.append(
                        GraphNodeResult(
                            node_id=nid,
                            name=self.specs[nid].name,
                            status=NodeStatus.skipped,
                            error="upstream failure",
                        )
                    )
                continue

            if len(wave) == 1:
                nid, node_result, out = self._run_one(wave[0], bag)
                results.append(node_result)
                if node_result.status == NodeStatus.failed:
                    failed = True
                else:
                    bag.update(out)
                continue

            # Parallel fan-out within wave
            wave_outputs: dict[str, dict[str, Any]] = {}
            with ThreadPoolExecutor(max_workers=min(self.max_workers, len(wave))) as pool:
                futures = {pool.submit(self._run_one, nid, bag): nid for nid in wave}
                for fut in as_completed(futures):
                    nid, node_result, out = fut.result()
                    results.append(node_result)
                    if node_result.status == NodeStatus.failed:
                        failed = True
                    else:
                        wave_outputs[nid] = out

            for out in wave_outputs.values():
                bag.update(out)

        # Stable order by node id
        order = {n.id: i for i, n in enumerate(NODES)}
        results.sort(key=lambda r: order.get(r.node_id, 99))
        return bag, results

    def describe(self) -> dict[str, Any]:
        return {
            "nodes": [
                {
                    "id": n.id,
                    "name": n.name,
                    "role": n.role,
                    "parallel_group": n.parallel_group,
                    "is_verifier": n.is_verifier,
                    "inputs": list(n.inputs),
                    "outputs": list(n.outputs),
                }
                for n in NODES
            ],
            "edges": [{"from": a, "to": b} for a, b in EDGES],
            "waves": self.waves,
        }


def _summarize(value: Any) -> Any:
    """Keep node_results JSON-friendly and small."""
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        if isinstance(value, str) and len(value) > 400:
            return value[:400] + "…"
        return value
    if isinstance(value, dict):
        # Drop huge file bodies from summaries
        if "files" in value and isinstance(value["files"], dict):
            return {
                **{k: v for k, v in value.items() if k != "files"},
                "files": list(value["files"].keys())[:50],
                "file_count": len(value["files"]),
            }
        if "code" in value and isinstance(value.get("code"), str):
            return {
                **{k: (v[:200] + "…" if k == "code" and isinstance(v, str) and len(v) > 200 else v)
                   for k, v in value.items()},
            }
        return {k: _summarize(v) for k, v in list(value.items())[:40]}
    if isinstance(value, list):
        return [_summarize(v) for v in value[:30]]
    return str(value)[:200]
