"""CLI for Matrixly InvoiceForge."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .config import load_config
from .orchestrator import InvoiceForge

console = Console()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="invoice-forge", description="Matrixly InvoiceForge")
    p.add_argument(
        "command",
        choices=[
            "status",
            "demo",
            "process",
            "watch",
            "list",
            "exceptions",
            "pending",
            "approve",
            "reject",
            "reminders",
            "report",
            "usage",
            "serve",
        ],
    )
    p.add_argument("path", nargs="?", help="File path for process")
    p.add_argument("--id", help="HITL action id")
    p.add_argument("--json", action="store_true")
    p.add_argument("--host", default=None)
    p.add_argument("--port", type=int, default=None)
    args = p.parse_args(argv)

    cfg = load_config()
    agent = InvoiceForge(cfg)

    if args.command == "status":
        st = agent.status()
        print(json.dumps(st, indent=2) if args.json else Panel.fit(json.dumps(st, indent=2), title="InvoiceForge"))
        return 0

    if args.command == "demo":
        results = agent.demo()
        for r in results:
            inv = r.invoice
            console.rule(inv.source_file or inv.id)
            console.print(
                f"[cyan]status={inv.status.value} conf={inv.confidence:.2f} "
                f"vendor={inv.vendor_name} total={inv.total}[/cyan]"
            )
            console.print(r.message)
            if inv.exceptions:
                console.print(f"[yellow]exceptions: {inv.exceptions}[/yellow]")
            console.print()
        return 0

    if args.command == "process":
        if not args.path:
            console.print("[red]Provide file path[/red]")
            return 1
        path = Path(args.path)
        if not path.exists():
            console.print("[red]File not found[/red]")
            return 1
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
            res = agent.process_file(path)
        else:
            res = agent.process_text(path.read_text(encoding="utf-8", errors="ignore"), filename=path.name)
        if args.json:
            print(json.dumps(res.invoice.model_dump(), indent=2))
        else:
            console.print(Panel(res.message, title=res.invoice.status.value))
            console.print(res.invoice.model_dump())
        return 0

    if args.command == "watch":
        r1 = agent.watch_uploads()
        r2 = agent.watch_email()
        console.print(f"uploads={len(r1)} email={len(r2)}")
        return 0

    if args.command == "list":
        items = agent.store.list()
        if args.json:
            print(json.dumps([i.model_dump() for i in items], indent=2))
            return 0
        table = Table(title="Invoices")
        table.add_column("id")
        table.add_column("vendor")
        table.add_column("number")
        table.add_column("total")
        table.add_column("status")
        for i in items:
            table.add_row(
                i.id,
                i.vendor_name or "—",
                i.invoice_number or "—",
                str(i.total) if i.total is not None else "—",
                i.status.value,
            )
        console.print(table)
        return 0

    if args.command == "exceptions":
        items = agent.store.list_exceptions()
        print(json.dumps([i.model_dump() for i in items], indent=2))
        return 0

    if args.command == "pending":
        print(json.dumps([a.model_dump() for a in agent.hitl.list_pending()], indent=2))
        return 0

    if args.command == "approve":
        if not args.id:
            return 1
        inv = agent.approve_hitl(args.id)
        console.print(inv.model_dump() if inv else "not found")
        return 0 if inv else 1

    if args.command == "reject":
        if not args.id:
            return 1
        inv = agent.reject_hitl(args.id)
        console.print(inv.model_dump() if inv else "not found")
        return 0 if inv else 1

    if args.command == "reminders":
        n = agent.process_reminders()
        console.print(f"[green]Sent {n} reminder(s)[/green]")
        return 0

    if args.command == "report":
        r = agent.report()
        if args.json:
            print(json.dumps(r["summary"], indent=2))
        else:
            console.print(r["markdown"])
        return 0

    if args.command == "usage":
        print(json.dumps(agent.usage.summary(30), indent=2))
        return 0

    if args.command == "serve":
        import uvicorn

        host = args.host or (cfg.get("server") or {}).get("host") or "0.0.0.0"
        port = args.port or int((cfg.get("server") or {}).get("port") or 8791)
        console.print(f"Serving InvoiceForge on http://{host}:{port}")
        uvicorn.run("src.main:app", host=host, port=port, reload=False)
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
