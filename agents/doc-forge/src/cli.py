"""CLI for DocForge."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from .config import load_config
from .orchestrator import DocForge

console = Console()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="doc-forge")
    p.add_argument(
        "command",
        choices=[
            "status",
            "demo",
            "draft",
            "list",
            "templates",
            "pending",
            "approve",
            "reject",
            "export",
            "send",
            "usage",
            "serve",
        ],
    )
    p.add_argument("path", nargs="?", help="JSON brief for draft")
    p.add_argument("--id", help="HITL or document id")
    p.add_argument("--type", default="proposal", help="proposal|quote|contract|report")
    p.add_argument("--formats", default="md,html,pdf,txt")
    p.add_argument("--json", action="store_true")
    p.add_argument("--host", default=None)
    p.add_argument("--port", type=int, default=None)
    args = p.parse_args(argv)

    cfg = load_config()
    agent = DocForge(cfg)

    if args.command == "status":
        st = agent.status()
        print(json.dumps(st, indent=2) if args.json else Panel.fit(json.dumps(st, indent=2), title="DocForge"))
        return 0

    if args.command == "demo":
        doc = agent.demo()
        console.print(
            f"[green]doc={doc.id} status={doc.status.value} type={doc.doc_type.value} "
            f"quality={doc.quality_score} exports={len(doc.export_paths)}[/green]"
        )
        console.print(doc.title)
        return 0

    if args.command == "draft":
        if args.path:
            data = json.loads(Path(args.path).read_text(encoding="utf-8"))
            doc = agent.draft(
                doc_type=data.get("doc_type") or args.type,
                client=data.get("client"),
                project=data.get("project"),
                line_items=data.get("line_items"),
                discount_pct=float(data.get("discount_pct") or 0),
                notes=str(data.get("notes") or ""),
                source="manual",
            )
        else:
            doc = agent.draft(source="sample", doc_type=args.type)
        if args.json:
            print(json.dumps(doc.model_dump(), indent=2))
        else:
            console.print(Panel(doc.title or doc.id, title=doc.status.value))
            console.print(doc.summary)
        return 0

    if args.command == "list":
        print(json.dumps([d.model_dump() for d in agent.store.list()], indent=2))
        return 0

    if args.command == "templates":
        print(json.dumps(agent.templates.list(), indent=2))
        return 0

    if args.command == "pending":
        print(json.dumps([a.model_dump() for a in agent.hitl.list_pending()], indent=2))
        return 0

    if args.command == "approve":
        if not args.id:
            return 1
        doc = agent.approve(args.id)
        console.print(doc.model_dump() if doc else "not found")
        return 0 if doc else 1

    if args.command == "reject":
        if not args.id:
            return 1
        doc = agent.reject(args.id)
        console.print(doc.model_dump() if doc else "not found")
        return 0 if doc else 1

    if args.command == "export":
        if not args.id:
            return 1
        fmts = [x.strip() for x in args.formats.split(",") if x.strip()]
        doc = agent.export(args.id, fmts)
        console.print(doc.export_paths if doc else "not found")
        return 0 if doc else 1

    if args.command == "send":
        if not args.id:
            return 1
        doc = agent.send(args.id)
        console.print(doc.model_dump() if doc else "not found")
        return 0 if doc else 1

    if args.command == "usage":
        print(json.dumps(agent.usage.summary(), indent=2))
        return 0

    if args.command == "serve":
        import uvicorn

        host = args.host or (cfg.get("server") or {}).get("host") or "0.0.0.0"
        port = args.port or int((cfg.get("server") or {}).get("port") or 8796)
        uvicorn.run("src.main:app", host=host, port=port, reload=False)
        return 0

    return 1
