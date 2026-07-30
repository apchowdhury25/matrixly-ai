"""CLI for SEOForge."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from .config import load_config
from .orchestrator import SEOForge

console = Console()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="seo-forge")
    p.add_argument(
        "command",
        choices=[
            "status",
            "demo",
            "plan",
            "generate",
            "audit",
            "local",
            "chat",
            "list",
            "pending",
            "approve",
            "reject",
            "publish",
            "keywords",
            "roi",
            "usage",
            "serve",
        ],
    )
    p.add_argument("path", nargs="?", help="Input file for plan/generate/audit")
    p.add_argument("--id", help="HITL or job id")
    p.add_argument("--text", help="Chat message or free text")
    p.add_argument("--type", dest="content_type", default="blog")
    p.add_argument("--keyword", default="")
    p.add_argument("--targets", default="local")
    p.add_argument("--json", action="store_true")
    p.add_argument("--host", default=None)
    p.add_argument("--port", type=int, default=None)
    args = p.parse_args(argv)

    cfg = load_config()
    agent = SEOForge(cfg)

    if args.command == "status":
        st = agent.status()
        print(json.dumps(st, indent=2) if args.json else Panel.fit(json.dumps(st, indent=2), title="SEOForge"))
        return 0

    if args.command == "demo":
        job = agent.demo()
        console.print(
            f"[green]job={job.id} status={job.status.value} "
            f"title={(job.draft or {}).get('title')}[/green]"
        )
        return 0

    if args.command == "plan":
        text = args.text
        if args.path:
            text = Path(args.path).read_text(encoding="utf-8", errors="ignore")
        if not text:
            console.print("[red]text or path required[/red]")
            return 1
        job = agent.create_plan(text)
        print(json.dumps(job.model_dump(), indent=2) if args.json else job.plan)
        return 0

    if args.command == "generate":
        text = args.text
        if args.path:
            text = Path(args.path).read_text(encoding="utf-8", errors="ignore")
        if not text:
            console.print("[red]text or path required[/red]")
            return 1
        job = agent.generate_content(
            text,
            content_type=args.content_type,
            primary_keyword=args.keyword,
        )
        if args.json:
            print(json.dumps(job.model_dump(), indent=2))
        else:
            console.print(Panel((job.draft or {}).get("title") or job.id, title=job.status.value))
        return 0

    if args.command == "audit":
        if not args.path:
            console.print("[red]path required[/red]")
            return 1
        text = Path(args.path).read_text(encoding="utf-8", errors="ignore")
        job = agent.audit_page(text, url_or_title=Path(args.path).stem, primary_keyword=args.keyword)
        print(json.dumps(job.audit, indent=2))
        return 0

    if args.command == "local":
        text = args.text
        if args.path:
            text = Path(args.path).read_text(encoding="utf-8", errors="ignore")
        if not text:
            console.print("[red]text or path required[/red]")
            return 1
        job = agent.local_package(text)
        print(json.dumps(job.local, indent=2))
        return 0

    if args.command == "chat":
        msg = args.text or "Help me grow local SEO for my US small business."
        print(json.dumps(agent.chat(msg), indent=2))
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

    if args.command == "keywords":
        print(json.dumps({"items": agent.keywords.list(), "summary": agent.keywords.summary()}, indent=2))
        return 0

    if args.command == "roi":
        print(json.dumps({"summary": agent.roi.summary(), "events": agent.roi.events(20)}, indent=2))
        return 0

    if args.command == "usage":
        print(json.dumps(agent.usage.summary(30), indent=2))
        return 0

    if args.command == "serve":
        import uvicorn

        host = args.host or (cfg.get("server") or {}).get("host") or "0.0.0.0"
        port = args.port or int((cfg.get("server") or {}).get("port") or 8798)
        console.print(f"Serving SEOForge on http://{host}:{port}")
        uvicorn.run("src.main:app", host=host, port=port, reload=False)
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
