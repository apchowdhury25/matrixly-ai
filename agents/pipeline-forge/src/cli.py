"""CLI for PipelineForge."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from .config import load_config
from .orchestrator import PipelineForge

console = Console()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="pipeline-forge")
    p.add_argument(
        "command",
        choices=[
            "status",
            "demo",
            "analyze",
            "list",
            "priority",
            "pending",
            "approve",
            "reject",
            "apply-crm",
            "usage",
            "serve",
        ],
    )
    p.add_argument("path", nargs="?", help="JSON pipeline file for analyze")
    p.add_argument("--id", help="HITL or run id")
    p.add_argument("--cadence", default="daily", help="daily|weekly")
    p.add_argument("--source", default="sample", help="sample|crm|payload")
    p.add_argument("--json", action="store_true")
    p.add_argument("--host", default=None)
    p.add_argument("--port", type=int, default=None)
    args = p.parse_args(argv)

    cfg = load_config()
    agent = PipelineForge(cfg)

    if args.command == "status":
        st = agent.status()
        print(json.dumps(st, indent=2) if args.json else Panel.fit(json.dumps(st, indent=2), title="PipelineForge"))
        return 0

    if args.command == "demo":
        run = agent.demo()
        console.print(
            f"[green]run={run.id} status={run.status.value} "
            f"scores={len(run.scores)} priority={len(run.priority_list)} risks={len(run.risks)}[/green]"
        )
        console.print(run.list_title)
        if run.insights:
            console.print(f"health={run.insights.get('health_score')}")
        return 0

    if args.command == "analyze":
        if args.path:
            data = json.loads(Path(args.path).read_text(encoding="utf-8"))
            run = agent.analyze(data, cadence=args.cadence, source="payload")
        else:
            run = agent.analyze(cadence=args.cadence, source=args.source)
        if args.json:
            print(json.dumps(run.model_dump(), indent=2))
        else:
            console.print(Panel(run.list_title or run.id, title=run.status.value))
            for item in run.priority_list[:8]:
                console.print(f"{item.rank}. [{item.score}] {item.name} — {item.next_action}")
        return 0

    if args.command == "list":
        print(json.dumps([r.model_dump() for r in agent.store.list()], indent=2))
        return 0

    if args.command == "priority":
        print(json.dumps(agent.store.latest_list() or {}, indent=2))
        return 0

    if args.command == "pending":
        print(json.dumps([a.model_dump() for a in agent.hitl.list_pending()], indent=2))
        return 0

    if args.command == "approve":
        if not args.id:
            return 1
        run = agent.approve(args.id)
        console.print(run.model_dump() if run else "not found")
        return 0 if run else 1

    if args.command == "reject":
        if not args.id:
            return 1
        run = agent.reject(args.id)
        console.print(run.model_dump() if run else "not found")
        return 0 if run else 1

    if args.command == "apply-crm":
        if not args.id:
            return 1
        run = agent.apply_crm(args.id)
        console.print(run.model_dump() if run else "not found")
        return 0 if run else 1

    if args.command == "usage":
        print(json.dumps(agent.usage.summary(), indent=2))
        return 0

    if args.command == "serve":
        import uvicorn

        host = args.host or (cfg.get("server") or {}).get("host") or "0.0.0.0"
        port = args.port or int((cfg.get("server") or {}).get("port") or 8795)
        uvicorn.run("src.main:app", host=host, port=port, reload=False)
        return 0

    return 1
