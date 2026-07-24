"""CLI for Matrixly BookWise."""

from __future__ import annotations

import argparse
import json

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .config import load_config
from .orchestrator import BookWise

console = Console()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="book-wise", description="Matrixly BookWise")
    p.add_argument(
        "command",
        choices=[
            "status",
            "demo",
            "chat",
            "availability",
            "upcoming",
            "pending",
            "approve",
            "reject",
            "reminders",
            "usage",
            "serve",
        ],
    )
    p.add_argument("text", nargs="?", help="Message for chat")
    p.add_argument("--id", help="HITL or booking id")
    p.add_argument("--service", default="consult")
    p.add_argument("--json", action="store_true")
    p.add_argument("--host", default=None)
    p.add_argument("--port", type=int, default=None)
    args = p.parse_args(argv)

    cfg = load_config()
    agent = BookWise(cfg)

    if args.command == "status":
        st = agent.status()
        print(json.dumps(st, indent=2) if args.json else Panel.fit(json.dumps(st, indent=2), title="BookWise"))
        return 0

    if args.command == "availability":
        slots = agent.calendar.propose_slots(service_id=args.service)
        if args.json:
            print(json.dumps([s.model_dump() for s in slots], indent=2))
        else:
            for i, s in enumerate(slots, 1):
                console.print(f"{i}. {s.label}  ({s.start_iso})")
        return 0

    if args.command == "demo":
        sid = None
        steps = [
            "What times are available this week for a consultation?",
            "Book the first available. My name is Alex Rivera and email is alex@acme.com",
            "When is my appointment?",
        ]
        for q in steps:
            console.rule(q[:70])
            state = agent.process(q, channel="chat", session_id=sid)
            sid = state.session_id
            console.print(f"[cyan]intent={state.intent.value}[/cyan]")
            console.print(state.reply)
            if state.booking:
                console.print(f"[green]booking={state.booking.id}[/green]")
            console.print()
        # cancel demo path
        if state.booking:
            console.rule("Cancel demo")
            c = agent.process(
                f"Please cancel {state.booking.id}",
                channel="chat",
                booking_id=state.booking.id,
            )
            console.print(c.reply)
        return 0

    if args.command == "chat":
        if not args.text:
            console.print("[red]Provide message text[/red]")
            return 1
        state = agent.process(args.text, channel="chat")
        if args.json:
            print(
                json.dumps(
                    {
                        "reply": state.reply,
                        "intent": state.intent.value,
                        "proposals": [p.model_dump() for p in state.proposals],
                        "booking": state.booking.model_dump() if state.booking else None,
                    },
                    indent=2,
                )
            )
        else:
            console.print(Panel(state.reply, title=state.intent.value))
        return 0

    if args.command == "upcoming":
        items = agent.bookings.list(upcoming_only=True)
        if args.json:
            print(json.dumps([b.model_dump() for b in items], indent=2))
            return 0
        table = Table(title="Upcoming bookings")
        table.add_column("id")
        table.add_column("when")
        table.add_column("who")
        table.add_column("service")
        for b in items:
            table.add_row(
                b.id,
                b.start_iso[:16],
                b.customer.email or b.customer.name or "—",
                b.service_name,
            )
        console.print(table)
        return 0

    if args.command == "pending":
        items = agent.hitl.list_pending()
        print(json.dumps([i.model_dump() for i in items], indent=2))
        return 0

    if args.command == "approve":
        if not args.id:
            return 1
        a = agent.hitl.decide(args.id, approve=True)
        console.print(a.model_dump() if a else "not found")
        return 0 if a else 1

    if args.command == "reject":
        if not args.id:
            return 1
        a = agent.hitl.decide(args.id, approve=False)
        console.print(a.model_dump() if a else "not found")
        return 0 if a else 1

    if args.command == "reminders":
        due = agent.reminders.due()
        for item in due:
            console.print(f"- {item['id']} → {item['message'][:80]}")
            agent.reminders.mark_sent(item["id"])
        console.print(f"[green]Sent {len(due)} reminder(s)[/green]")
        return 0

    if args.command == "usage":
        print(json.dumps(agent.usage.summary(30), indent=2))
        return 0

    if args.command == "serve":
        import uvicorn

        host = args.host or (cfg.get("server") or {}).get("host") or "0.0.0.0"
        port = args.port or int((cfg.get("server") or {}).get("port") or 8790)
        console.print(f"Serving BookWise on http://{host}:{port}")
        uvicorn.run("src.main:app", host=host, port=port, reload=False)
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
