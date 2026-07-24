"""CLI for ContentForge."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from .config import load_config
from .orchestrator import ContentForge

console = Console()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="content-forge")
    p.add_argument(
        "command",
        choices=[
            "status",
            "demo",
            "generate",
            "ideas",
            "list",
            "pending",
            "approve",
            "reject",
            "publish",
            "usage",
            "serve",
        ],
    )
    p.add_argument("path", nargs="?", help="Source file for generate")
    p.add_argument("--id", help="HITL or job id")
    p.add_argument("--text", help="Business input for ideas")
    p.add_argument("--targets", default="local", help="Publish targets comma-list")
    p.add_argument("--json", action="store_true")
    p.add_argument("--host", default=None)
    p.add_argument("--port", type=int, default=None)
    args = p.parse_args(argv)

    cfg = load_config()
    agent = ContentForge(cfg)

    if args.command == "status":
        st = agent.status()
        print(json.dumps(st, indent=2) if args.json else Panel.fit(json.dumps(st, indent=2), title="ContentForge"))
        return 0

    if args.command == "demo":
        job = agent.demo()
        console.print(f"[green]job={job.id} status={job.status.value} quality={job.quality_score}[/green]")
        console.print((job.edited or {}).get("title"))
        console.print(f"assets: {list((job.assets or {}).keys())}")
        return 0

    if args.command == "generate":
        if not args.path:
            console.print("[red]path required[/red]")
            return 1
        text = Path(args.path).read_text(encoding="utf-8", errors="ignore")
        job = agent.generate(text, source_title=Path(args.path).stem)
        if args.json:
            print(json.dumps(job.model_dump(), indent=2))
        else:
            console.print(Panel((job.edited or {}).get("title") or job.id, title=job.status.value))
        return 0

    if args.command == "ideas":
        text = args.text or "AI agents for small business marketing"
        print(json.dumps(agent.suggest_ideas(text), indent=2))
        return 0

    if args.command == "list":
        print(json.dumps([j.model_dump() for j in agent.store.list()], indent=2))
        return 0

    if args.command == "pending":
        print(json.dumps([a.model_dump() for a in agent.hitl.list_pending()], indent=2))
        return 0

    if args.command == "approve":
        if not args.id:
            return 1
        job = agent.approve(args.id)
        console.print(job.model_dump() if job else "not found")
        return 0 if job else 1

    if args.command == "reject":
        if not args.id:
            return 1
        job = agent.reject(args.id)
        console.print(job.model_dump() if job else "not found")
        return 0 if job else 1

    if args.command == "publish":
        if not args.id:
            return 1
        targets = [t.strip() for t in args.targets.split(",") if t.strip()]
        print(json.dumps(agent.publish(args.id, targets=targets), indent=2))
        return 0

    if args.command == "usage":
        print(json.dumps(agent.usage.summary(30), indent=2))
        return 0

    if args.command == "serve":
        import uvicorn

        host = args.host or (cfg.get("server") or {}).get("host") or "0.0.0.0"
        port = args.port or int((cfg.get("server") or {}).get("port") or 8792)
        console.print(f"Serving ContentForge on http://{host}:{port}")
        uvicorn.run("src.main:app", host=host, port=port, reload=False)
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
