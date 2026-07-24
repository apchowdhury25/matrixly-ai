"""CLI for MeetWise."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from .config import load_config
from .orchestrator import MeetWise

console = Console()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="meet-wise")
    p.add_argument(
        "command",
        choices=[
            "status",
            "demo",
            "process",
            "list",
            "pending",
            "approve",
            "reject",
            "usage",
            "serve",
        ],
    )
    p.add_argument("path", nargs="?", help="Transcript file")
    p.add_argument("--id", help="HITL id")
    p.add_argument("--json", action="store_true")
    p.add_argument("--host", default=None)
    p.add_argument("--port", type=int, default=None)
    args = p.parse_args(argv)

    cfg = load_config()
    agent = MeetWise(cfg)

    if args.command == "status":
        st = agent.status()
        print(json.dumps(st, indent=2) if args.json else Panel.fit(json.dumps(st, indent=2), title="MeetWise"))
        return 0

    if args.command == "demo":
        m = agent.demo()
        console.print(f"[green]{m.id}[/green] status={m.status.value} actions={len(m.action_items)}")
        console.print(m.summary[:400])
        return 0

    if args.command == "process":
        if not args.path:
            console.print("[red]path required[/red]")
            return 1
        m = agent.process_file(args.path)
        if args.json:
            print(json.dumps(m.model_dump(), indent=2))
        else:
            console.print(Panel(m.summary, title=m.title or m.id))
            for a in m.action_items:
                console.print(f"- {a.description} [{a.owner}/{a.deadline}]")
        return 0

    if args.command == "list":
        print(json.dumps([m.model_dump() for m in agent.store.list()], indent=2))
        return 0

    if args.command == "pending":
        print(json.dumps([a.model_dump() for a in agent.hitl.list_pending()], indent=2))
        return 0

    if args.command == "approve":
        if not args.id:
            return 1
        m = agent.approve(args.id)
        console.print(m.model_dump() if m else "not found")
        return 0 if m else 1

    if args.command == "reject":
        if not args.id:
            return 1
        m = agent.reject(args.id)
        console.print(m.model_dump() if m else "not found")
        return 0 if m else 1

    if args.command == "usage":
        print(json.dumps(agent.usage.summary(30), indent=2))
        return 0

    if args.command == "serve":
        import uvicorn

        host = args.host or (cfg.get("server") or {}).get("host") or "0.0.0.0"
        port = args.port or int((cfg.get("server") or {}).get("port") or 8793)
        console.print(f"Serving MeetWise on http://{host}:{port}")
        uvicorn.run("src.main:app", host=host, port=port, reload=False)
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
