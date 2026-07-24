"""CLI for Matrixly SupportForge."""

from __future__ import annotations

import argparse
import json
import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .config import load_config
from .orchestrator import SupportForge

console = Console()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="support-forge",
        description="Matrixly SupportForge — AI customer support agent",
    )
    p.add_argument(
        "command",
        choices=[
            "status",
            "seed",
            "demo",
            "chat",
            "pending",
            "approve",
            "reject",
            "usage",
            "followups",
            "serve",
            "ingest-email",
        ],
    )
    p.add_argument("text", nargs="?", help="Message text for chat")
    p.add_argument("--id", help="HITL action id")
    p.add_argument("--json", action="store_true")
    p.add_argument("--host", default=None)
    p.add_argument("--port", type=int, default=None)
    args = p.parse_args(argv)

    cfg = load_config()
    forge = SupportForge(cfg)

    if args.command == "status":
        st = forge.status()
        if args.json:
            print(json.dumps(st, indent=2))
        else:
            console.print(Panel.fit(json.dumps(st, indent=2), title="SupportForge"))
        return 0

    if args.command == "seed":
        result = forge.seed_knowledge()
        console.print(f"[green]Indexed[/green] {result}")
        return 0

    if args.command == "demo":
        samples = [
            "What are your pricing plans for SupportForge?",
            "What are your business hours?",
            "How do I track my order ORD-12345?",
            "My widget is not loading on the website.",
            "I want to speak to a lawyer about a lawsuit and chargeback fraud!",
        ]
        for q in samples:
            console.rule(q[:60])
            state = forge.process(q, channel="chat")
            console.print(
                f"[cyan]action={state.action.value} conf={state.confidence:.2f} "
                f"topic={state.topic.value} urgency={state.urgency.value}[/cyan]"
            )
            console.print(state.answer)
            console.print()
        return 0

    if args.command == "chat":
        if not args.text:
            console.print("[red]Provide message text[/red]")
            return 1
        state = forge.process(args.text, channel="chat")
        if args.json:
            print(
                json.dumps(
                    {
                        "reply": state.answer,
                        "action": state.action.value,
                        "confidence": state.confidence,
                        "ticket_id": state.ticket_id,
                        "hitl_id": state.hitl_id,
                    },
                    indent=2,
                )
            )
        else:
            console.print(
                Panel(
                    state.answer,
                    title=f"{state.action.value} · conf {state.confidence:.2f}",
                )
            )
        return 0

    if args.command == "pending":
        items = forge.hitl.list_pending()
        if args.json:
            print(json.dumps([i.model_dump() for i in items], indent=2))
            return 0
        table = Table(title="Pending HITL")
        table.add_column("id")
        table.add_column("kind")
        table.add_column("ticket")
        for i in items:
            table.add_row(i.id, i.kind, i.ticket_id or "")
        console.print(table)
        return 0

    if args.command == "approve":
        if not args.id:
            console.print("[red]--id required[/red]")
            return 1
        a = forge.hitl.decide(args.id, approve=True)
        if not a:
            console.print("[red]Not found[/red]")
            return 1
        console.print(f"[green]Approved[/green] {a.id}")
        return 0

    if args.command == "reject":
        if not args.id:
            console.print("[red]--id required[/red]")
            return 1
        a = forge.hitl.decide(args.id, approve=False)
        if not a:
            console.print("[red]Not found[/red]")
            return 1
        console.print(f"[yellow]Rejected[/yellow] {a.id}")
        return 0

    if args.command == "usage":
        s = forge.usage.summary(days=30)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            console.print(Panel.fit(json.dumps(s, indent=2), title="Usage (30d)"))
        return 0

    if args.command == "followups":
        due = forge.followups.due()
        if args.json:
            print(json.dumps(due, indent=2))
            return 0
        for item in due:
            console.print(f"- {item['id']} ticket={item['ticket_id']} → {item['message'][:80]}")
            forge.followups.mark_done(item["id"])
        console.print(f"[green]Processed {len(due)} follow-up(s)[/green]")
        return 0

    if args.command == "ingest-email":
        from .integrations.email_ingest import fetch_imap_unseen
        from .models import Customer

        msgs = fetch_imap_unseen(cfg)
        if not msgs:
            console.print("[yellow]No IMAP messages (or EMAIL_BACKEND not imap)[/yellow]")
            return 0
        for m in msgs:
            state = forge.process(
                m.get("body") or "",
                channel="email",
                customer=Customer(name=m.get("from_name"), email=m.get("from_email")),
                subject=m.get("subject") or "",
            )
            console.print(f"Processed {m.get('from_email')} → {state.action.value}")
        return 0

    if args.command == "serve":
        import uvicorn

        host = args.host or (cfg.get("server") or {}).get("host") or "0.0.0.0"
        port = args.port or int((cfg.get("server") or {}).get("port") or 8787)
        console.print(f"Serving SupportForge on http://{host}:{port}")
        uvicorn.run("src.main:app", host=host, port=port, reload=False)
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
