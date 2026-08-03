#!/usr/bin/env python3
"""Smoke test SEO-Bespoke full parallel graph without API key."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import load_config
from src.graph.topology import EDGES, NODES, topological_waves
from src.models import KeywordItem, RunStatus
from src.orchestrator import SEOBespoke


def main() -> int:
    assert len(NODES) == 20, f"expected 20 nodes, got {len(NODES)}"
    assert len(EDGES) >= 19, "graph should have real dependency edges"
    waves = topological_waves()
    assert waves[0] == ["N1"], f"entry wave should be N1, got {waves[0]}"
    # Collectors parallel
    assert set(waves[1]) == {"N2", "N3", "N4", "N5", "N6", "N7"}
    # Code generators parallel
    gen_wave = next(w for w in waves if "N11" in w)
    assert set(gen_wave) == {"N11", "N12", "N13", "N14", "N15", "N16"}

    cfg = load_config()
    agent = SEOBespoke(cfg)

    # Graph describe
    g = agent.graph_describe()
    assert g["node_count"] == 20
    assert "N9" in g["verifiers"] and "N18" in g["verifiers"]

    # Full demo pipeline
    run = agent.demo()
    assert run.id
    assert run.profile is not None
    assert run.profile.business_name == "Apex Comfort HVAC"
    assert run.profile.summary_markdown
    assert "Never invent" in run.profile.summary_markdown or any(
        "invent" in r.lower() for r in run.profile.safety_rules
    )
    assert run.package_path
    assert Path(run.package_path).exists()
    assert (Path(run.package_path) / "README.md").exists()
    assert (Path(run.package_path) / "agent" / "main.py").exists()
    assert (Path(run.package_path) / "brand" / "voice.md").exists()
    assert (Path(run.package_path) / "scripts" / "smoke_test.py").exists()

    # All 20 nodes completed
    completed = [n for n in run.node_results if n.status.value == "completed"]
    assert len(completed) == 20, f"expected 20 completed nodes, got {len(completed)}: {[n.node_id+':'+n.status.value for n in run.node_results]}"

    # Verifiers isolated
    n9 = next(n for n in run.node_results if n.node_id == "N9")
    assert n9.isolation == "isolated_context"
    assert "chat_history" not in n9.inputs_keys

    n18 = next(n for n in run.node_results if n.node_id == "N18")
    assert n18.isolation == "isolated_context"

    assert run.safety.get("ok") is True
    assert run.smoke.get("ok") is True
    assert run.status in {RunStatus.pending_review, RunStatus.completed, RunStatus.approved}

    # Generated package smoke already ran inside N20
    assert run.package.get("id")

    # Keywords seeded without ranks
    assert agent.keywords.summary()["total"] >= 1

    # ROI recorded
    assert agent.roi.summary()["hours_saved"] >= 4

    # Chat
    chat = agent.chat("show profile")
    assert chat.get("reply")
    assert "Apex Comfort" in chat["reply"] or "profile" in chat["reply"].lower()

    # HITL approve path
    if run.hitl_id:
        res = agent.approve_hitl(run.hitl_id, decided_by="smoke", note="smoke approve")
        assert res.get("ok")

    # Brand save
    brand = agent.brand.save_voice("# Voice\nLocal HVAC experts.\n", tone=["friendly"], avoid=["guarantees"])
    assert brand.get("ok")

    # Manual keyword + ROI
    agent.keywords.upsert(
        [
            KeywordItem(
                keyword="AC repair Austin",
                intent="local",
                priority="high",
                city="Austin, TX",
                current_rank=18,
            )
        ]
    )
    agent.roi.record(hours_saved=1, leads_attributed=1, revenue_usd=200, note="smoke manual")

    # Regenerate from profile
    run2 = agent.regenerate_from_profile(run.profile.id)
    assert run2.id != run.id
    assert run2.profile is not None
    assert Path(run2.package_path or "").exists()

    print(
        "SMOKE OK",
        {
            "run": run.id,
            "status": run.status.value,
            "nodes": len(completed),
            "profile": run.profile.id,
            "package": run.package.get("id"),
            "package_path": run.package_path,
            "hitl": run.hitl_id,
            "keywords": agent.keywords.summary(),
            "roi": agent.roi.summary(),
            "regen": run2.id,
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
