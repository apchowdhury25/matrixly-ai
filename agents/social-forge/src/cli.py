"""CLI for SocialForge."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from .config import load_config
from .orchestrator import SocialForge

console = Console()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="social-forge")
    p.add_argument(
        "command",
        choices=[
            "status",
            "demo",
            "compose",
            "list",
            "calendar",
            "monitor",
            "replies",
            "insights",
            "pending",
            "approve",
            "reject",
            "publish",
            "usage",
            "serve",
        ],
    )
    p.add_argument("path", nargs="?", help="Idea file for compose")
    p.add_argument("--id", help="HITL or campaign id")
    p.add_argument("--text", help="Idea text for compose")
    p.add_argument("--platforms", default="", help="Comma list: linkedin,x,instagram")
    p.add_argument("--targets", default="", help="Publish platforms comma-list")
    p.add_argument("--backend", default="", help="local|buffer|meta|linkedin")
    p.add_argument("--json", action="store_true")
    p.add_argument("--host", default=None)
    p.add_argument("--port", type=int, default=None)
    args = p.parse_args(argv)

    cfg = load_config()
    agent = SocialForge(cfg)

    if args.command == "status":
        st = agent.status()
        print(json.dumps(st, indent=2) if args.json else Panel.fit(json.dumps(st, indent=2), title="SocialForge"))
        return 0

    if args.command == "demo":
        c = agent.demo()
        console.print(f"[green]campaign={c.id} status={c.status.value} platforms={list(c.posts.keys())}[/green]")
        console.print(c.theme)
        return 0

    if args.command == "compose":
        if args.path:
            idea = Path(args.path).read_text(encoding="utf-8", errors="ignore")
        elif args.text:
            idea = args.text
        else:
            console.print("[red]path or --text required[/red]")
            return 1
        platforms = [x.strip() for x in args.platforms.split(",") if x.strip()] or None
        c = agent.compose(idea, platforms=platforms)
        if args.json:
            print(json.dumps(c.model_dump(), indent=2))
        else:
            console.print(Panel(c.theme or c.id, title=c.status.value))
            for plat, post in c.posts.items():
                console.print(f"\n[bold]{plat}[/bold]\n{post.text[:280]}")
        return 0

    if args.command == "list":
        print(json.dumps([c.model_dump() for c in agent.store.list_campaigns()], indent=2))
        return 0

    if args.command == "calendar":
        print(json.dumps(agent.store.list_schedule(), indent=2))
        return 0

    if args.command == "monitor":
        print(json.dumps(agent.monitor(), indent=2))
        return 0

    if args.command == "replies":
        print(json.dumps(agent.draft_replies(), indent=2))
        return 0

    if args.command == "insights":
        print(json.dumps(agent.insights().model_dump(), indent=2))
        return 0

    if args.command == "pending":
        print(json.dumps([a.model_dump() for a in agent.hitl.list_pending()], indent=2))
        return 0

    if args.command == "approve":
        if not args.id:
            return 1
        result = agent.approve(args.id)
        console.print(result.model_dump() if result else "not found")
        return 0 if result else 1

    if args.command == "reject":
        if not args.id:
            return 1
        result = agent.reject(args.id)
        console.print(result.model_dump() if result else "not found")
        return 0 if result else 1

    if args.command == "publish":
        if not args.id:
            return 1
        plats = [x.strip() for x in args.targets.split(",") if x.strip()] or None
        c = agent.publish(args.id, platforms=plats, backend=args.backend or None)
        console.print(c.model_dump() if c else "not found")
        return 0 if c else 1

    if args.command == "usage":
        print(json.dumps(agent.usage.summary(), indent=2))
        return 0

    if args.command == "serve":
        import uvicorn

        host = args.host or (cfg.get("server") or {}).get("host") or "0.0.0.0"
        port = args.port or int((cfg.get("server") or {}).get("port") or 8794)
        uvicorn.run("src.main:app", host=host, port=port, reload=False)
        return 0

    return 1
