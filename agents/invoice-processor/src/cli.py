"""CLI for Matrixly Invoice Processor."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .deps import InvoiceProcessorDeps
from .models import InvoiceInput, SourceType
from .pipeline import process_invoice

console = Console()
ROOT = Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="invoice-processor",
        description="Matrixly Invoice Processor — Pydantic AI multi-agent AP",
    )
    p.add_argument(
        "command",
        choices=["process", "demo", "smoke", "list-pos", "serve", "example"],
    )
    p.add_argument("path", nargs="?", help="Invoice file (.txt / .pdf)")
    p.add_argument("--text", help="Inline invoice text")
    p.add_argument("--no-llm", action="store_true", help="Force rule-based specialists")
    p.add_argument("--orchestrator-llm", action="store_true", help="Use agentic orchestrator")
    p.add_argument("--json", action="store_true")
    p.add_argument("--host", default=None)
    p.add_argument("--port", type=int, default=None)
    args = p.parse_args(argv)

    if args.command == "list-pos":
        deps = InvoiceProcessorDeps.create()
        pos = deps.po_store.list_all()
        if args.json:
            print(json.dumps([x.model_dump() for x in pos], indent=2))
        else:
            table = Table(title="Purchase Orders")
            table.add_column("PO")
            table.add_column("Vendor")
            table.add_column("Total")
            table.add_column("Status")
            for po in pos:
                table.add_row(po.po_number, po.vendor_name, f"${po.total:.2f}", po.status)
            console.print(table)
        return 0

    if args.command == "smoke":
        sys.path.insert(0, str(ROOT))
        from scripts.smoke_test import main as smoke_main  # type: ignore

        return smoke_main()

    if args.command in {"process", "demo", "example"}:
        deps = InvoiceProcessorDeps.create()
        use_llm = False if args.no_llm else None

        if args.command in {"demo", "example"}:
            sample = ROOT / "samples" / "invoice_acme_match.txt"
            text = sample.read_text(encoding="utf-8")
            payload = InvoiceInput(text=text, source_type=SourceType.text, filename=sample.name)
        elif args.text:
            payload = InvoiceInput(text=args.text, source_type=SourceType.text)
        elif args.path:
            path = Path(args.path)
            if path.suffix.lower() == ".pdf":
                payload = InvoiceInput(
                    pdf_path=str(path), source_type=SourceType.pdf, filename=path.name
                )
            else:
                payload = InvoiceInput(
                    text=path.read_text(encoding="utf-8", errors="ignore"),
                    source_type=SourceType.text,
                    filename=path.name,
                )
        else:
            console.print("[red]Provide path, --text, or use demo[/red]")
            return 1

        if args.orchestrator_llm:
            from .agents.orchestrator import run_orchestrator

            result = asyncio.run(
                run_orchestrator(deps, payload, use_llm_orchestrator=True)
            )
        else:
            result = asyncio.run(process_invoice(deps, payload, use_llm=use_llm))

        if args.json:
            print(result.model_dump_json(indent=2))
        else:
            _print_result(result)
        return 0 if result.status.value != "failed" else 1

    if args.command == "serve":
        import uvicorn

        host = args.host or "0.0.0.0"
        port = args.port or 8799
        console.print(f"Serving Invoice Processor API on http://{host}:{port}")
        uvicorn.run("src.main:app", host=host, port=port, reload=False)
        return 0

    return 1


def _print_result(result) -> None:
    inv = result.invoice
    match = result.matching
    rev = result.review
    console.print(
        Panel.fit(
            f"[bold]{inv.vendor_name}[/bold] · INV {inv.invoice_number}\n"
            f"PO: {inv.po_number or '—'} · Total: {inv.currency} {inv.total:.2f}\n"
            f"Extract conf: {inv.extraction_confidence:.2f} ({inv.extraction_method})\n"
            f"Match: {match.status.value} ({match.match_confidence:.2f}) · "
            f"{len(match.discrepancies)} discrepancies\n"
            f"Review: [bold]{rev.action.value}[/bold] · HITL={rev.requires_human}\n"
            f"{rev.reasoning}",
            title=f"Invoice Processor · {result.processing_id}",
        )
    )
    if match.discrepancies:
        table = Table(title="Discrepancies")
        table.add_column("Severity")
        table.add_column("Type")
        table.add_column("Field")
        table.add_column("Description")
        for d in match.discrepancies:
            table.add_row(d.severity.value, d.type.value, d.field, d.description[:80])
        console.print(table)
    if rev.recommended_next_actions:
        console.print("[cyan]Next actions:[/cyan]")
        for a in rev.recommended_next_actions:
            console.print(f"  • {a}")


if __name__ == "__main__":
    raise SystemExit(main())
