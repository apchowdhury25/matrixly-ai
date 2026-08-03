"""
SEO-Bespoke parallel graph topology (exactly 20 nodes).

Design rules:
- Real edges only (data dependencies). Independent work fans out in parallel.
- Prefer width over depth; converge only when necessary.
- Verifiers (N9, N18) receive isolated context — no shared chat history.
- Max 20 agents/nodes total.

Topology:

  N1 Quiz Orchestrator
      │ fan-out (parallel, no edges between collectors)
      ├─► N2 Domain Collector
      ├─► N3 Industry Collector
      ├─► N4 Business Collector
      ├─► N5 Customers Collector
      ├─► N6 Location Collector
      └─► N7 Goals Collector
              │ converge
              ▼
          N8 Profile Synthesizer
              │
              ├─► N9 Summary Verifier  (isolated)
              │         │
              └────┬────┘
                   ▼
              N10 Code Architect
                   │ fan-out (parallel generators)
                   ├─► N11 Research Planner Gen
                   ├─► N12 Brand Voice Engine Gen
                   ├─► N13 Local SEO Gen
                   ├─► N14 Content Engine Gen
                   ├─► N15 Tracking Gen
                   └─► N16 ROI Gen
                            │ converge
                            ▼
                    N17 Code Assembler + Config Writer
                            │
                            ├─► N18 Safety & HITL Verifier  (isolated)
                            │         │
                            └────┬────┘
                                 ▼
                         N19 Deployment Package Builder
                                 │
                                 ▼
                         N20 Final Integration & Smoke-Test
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass(frozen=True)
class NodeSpec:
    id: str
    name: str
    role: str
    parallel_group: str | None = None  # same group → can run concurrently
    is_verifier: bool = False
    isolation: str = "pure_function"
    inputs: tuple[str, ...] = ()
    outputs: tuple[str, ...] = ()


NODES: list[NodeSpec] = [
    NodeSpec(
        id="N1",
        name="Quiz Orchestrator",
        role="entry",
        inputs=("quiz_raw",),
        outputs=("quiz_plan", "normalized_quiz"),
    ),
    NodeSpec(
        id="N2",
        name="Domain Collector",
        role="collector",
        parallel_group="quiz_collectors",
        inputs=("normalized_quiz",),
        outputs=("domain_slice",),
    ),
    NodeSpec(
        id="N3",
        name="Industry Collector",
        role="collector",
        parallel_group="quiz_collectors",
        inputs=("normalized_quiz",),
        outputs=("industry_slice",),
    ),
    NodeSpec(
        id="N4",
        name="Business Collector",
        role="collector",
        parallel_group="quiz_collectors",
        inputs=("normalized_quiz",),
        outputs=("business_slice",),
    ),
    NodeSpec(
        id="N5",
        name="Customers Collector",
        role="collector",
        parallel_group="quiz_collectors",
        inputs=("normalized_quiz",),
        outputs=("customers_slice",),
    ),
    NodeSpec(
        id="N6",
        name="Location Collector",
        role="collector",
        parallel_group="quiz_collectors",
        inputs=("normalized_quiz",),
        outputs=("location_slice",),
    ),
    NodeSpec(
        id="N7",
        name="Goals Collector",
        role="collector",
        parallel_group="quiz_collectors",
        inputs=("normalized_quiz",),
        outputs=("goals_slice",),
    ),
    NodeSpec(
        id="N8",
        name="Profile Synthesizer",
        role="synthesizer",
        inputs=(
            "domain_slice",
            "industry_slice",
            "business_slice",
            "customers_slice",
            "location_slice",
            "goals_slice",
        ),
        outputs=("profile", "summary_markdown"),
    ),
    NodeSpec(
        id="N9",
        name="Summary Verifier",
        role="verifier",
        is_verifier=True,
        isolation="isolated_context",
        inputs=("profile", "summary_markdown"),  # clean only — no chat history
        outputs=("profile_verification",),
    ),
    NodeSpec(
        id="N10",
        name="Code Architect",
        role="architect",
        inputs=("profile", "profile_verification"),
        outputs=("architecture",),
    ),
    NodeSpec(
        id="N11",
        name="Research Planner Generator",
        role="codegen",
        parallel_group="code_generators",
        inputs=("architecture", "profile"),
        outputs=("module_research",),
    ),
    NodeSpec(
        id="N12",
        name="Brand Voice Engine Generator",
        role="codegen",
        parallel_group="code_generators",
        inputs=("architecture", "profile"),
        outputs=("module_brand",),
    ),
    NodeSpec(
        id="N13",
        name="Local SEO Generator",
        role="codegen",
        parallel_group="code_generators",
        inputs=("architecture", "profile"),
        outputs=("module_local",),
    ),
    NodeSpec(
        id="N14",
        name="Content Engine Generator",
        role="codegen",
        parallel_group="code_generators",
        inputs=("architecture", "profile"),
        outputs=("module_content",),
    ),
    NodeSpec(
        id="N15",
        name="Tracking Generator",
        role="codegen",
        parallel_group="code_generators",
        inputs=("architecture", "profile"),
        outputs=("module_tracking",),
    ),
    NodeSpec(
        id="N16",
        name="ROI Generator",
        role="codegen",
        parallel_group="code_generators",
        inputs=("architecture", "profile"),
        outputs=("module_roi",),
    ),
    NodeSpec(
        id="N17",
        name="Code Assembler + Config Writer",
        role="assembler",
        inputs=(
            "architecture",
            "profile",
            "module_research",
            "module_brand",
            "module_local",
            "module_content",
            "module_tracking",
            "module_roi",
        ),
        outputs=("assembled_package", "config_files"),
    ),
    NodeSpec(
        id="N18",
        name="Safety & HITL Verifier",
        role="verifier",
        is_verifier=True,
        isolation="isolated_context",
        inputs=("assembled_package", "config_files", "profile"),  # isolated
        outputs=("safety_report",),
    ),
    NodeSpec(
        id="N19",
        name="Deployment Package Builder",
        role="packager",
        inputs=("assembled_package", "config_files", "safety_report", "profile"),
        outputs=("deployment_package",),
    ),
    NodeSpec(
        id="N20",
        name="Final Integration & Smoke-Test",
        role="smoke",
        inputs=("deployment_package", "safety_report"),
        outputs=("smoke_report", "final_manifest"),
    ),
]

# Real data-dependency edges only
EDGES: list[tuple[str, str]] = [
    # Entry → collectors
    ("N1", "N2"),
    ("N1", "N3"),
    ("N1", "N4"),
    ("N1", "N5"),
    ("N1", "N6"),
    ("N1", "N7"),
    # Collectors → synthesizer
    ("N2", "N8"),
    ("N3", "N8"),
    ("N4", "N8"),
    ("N5", "N8"),
    ("N6", "N8"),
    ("N7", "N8"),
    # Profile → verifier + architect
    ("N8", "N9"),
    ("N8", "N10"),
    ("N9", "N10"),
    # Architect → parallel generators
    ("N10", "N11"),
    ("N10", "N12"),
    ("N10", "N13"),
    ("N10", "N14"),
    ("N10", "N15"),
    ("N10", "N16"),
    # Generators → assembler
    ("N11", "N17"),
    ("N12", "N17"),
    ("N13", "N17"),
    ("N14", "N17"),
    ("N15", "N17"),
    ("N16", "N17"),
    # Assembler → safety + package
    ("N17", "N18"),
    ("N17", "N19"),
    ("N18", "N19"),
    # Package → smoke
    ("N19", "N20"),
    ("N18", "N20"),
]

assert len(NODES) == 20, f"Graph must have exactly 20 nodes, got {len(NODES)}"
assert len(NODES) <= 20

GRAPH_DESCRIPTION = {
    "name": "SEO-Bespoke Parallel Graph",
    "node_count": len(NODES),
    "edge_count": len(EDGES),
    "parallel_groups": {
        "quiz_collectors": ["N2", "N3", "N4", "N5", "N6", "N7"],
        "code_generators": ["N11", "N12", "N13", "N14", "N15", "N16"],
    },
    "verifiers": ["N9", "N18"],
    "critical_path": ["N1", "N2", "N8", "N9", "N10", "N11", "N17", "N18", "N19", "N20"],
    "principles": [
        "Real edges only — independent work fans out",
        "Verifiers get isolated context (no chat history)",
        "Width over depth",
        "Never invent stats/reviews/rankings",
        "HITL gate before package deploy",
    ],
}


def topological_waves() -> list[list[str]]:
    """Return execution waves (parallel sets) via Kahn-style leveling."""
    ids = {n.id for n in NODES}
    indeg = {i: 0 for i in ids}
    succ: dict[str, list[str]] = {i: [] for i in ids}
    for a, b in EDGES:
        succ[a].append(b)
        indeg[b] += 1

    waves: list[list[str]] = []
    ready = sorted([i for i, d in indeg.items() if d == 0])
    seen: set[str] = set()
    while ready:
        waves.append(ready[:])
        next_ready: list[str] = []
        for u in ready:
            seen.add(u)
            for v in succ[u]:
                indeg[v] -= 1
                if indeg[v] == 0 and v not in seen:
                    next_ready.append(v)
        ready = sorted(next_ready)
    return waves
