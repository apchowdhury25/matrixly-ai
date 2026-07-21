"""CLI: python -m src.cli <command>."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from .agent import CRMAssistant
from .config import load_config

console = Console()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="crm-assistant",
        description="Matrixly CRM Assistant — contacts, activities, hygiene, HITL writes",
    )
    p.add_argument(
        "command",
        choices=[
            "status",
            "note",
            "pending",
            "approve",
            "reject",
            "approve-all",
            "hygiene",
            "export",
            "seed",
            "contact",
            "activity",
            "demo",
        ],
    )
    p.add_argument("--text", "-t", help="Note / meeting / email text for note command")
    p.add_argument("--file", "-f", help="File path (seed JSON or note text file)")
    p.add_argument("--id", help="Write id for approve/reject")
    p.add_argument("--email", help="Contact email")
    p.add_argument("--name", help="Contact name")
    p.add_argument("--company", help="Company name")
    p.add_argument("--title", help="Title")
    p.add_argument("--subject", help="Activity subject")
    p.add_argument("--body", help="Activity body")
    p.add_argument("--type", dest="act_type", default="note", help="Activity type")
    p.add_argument("--apply", action="store_true", help="Apply immediately (skip queue)")
    p.add_argument("--no-llm", action="store_true")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    cfg = load_config()
    agent = CRMAssistant(cfg)

    try:
        if args.command == "status":
            console.print(Markdown(agent.status_report()))
            return 0

        if args.command == "demo":
            sample = Path(cfg["_paths"]["root"]) / "data" / "contacts" / "sample_crm.json"
            agent.seed_from_file(sample)
            note_path = Path(cfg["_paths"]["root"]) / "data" / "activities" / "sample_meeting_note.txt"
            text = note_path.read_text(encoding="utf-8")
            result = agent.process_note(text, source="meeting", use_llm=not args.no_llm, apply=False)
            hy = agent.hygiene()
            if args.json:
                print(json.dumps({"process": result, "hygiene": hy}, indent=2, default=str))
            else:
                console.print(Panel.fit("Seeded sample CRM + processed meeting note (queued writes)", title="Demo"))
                console.print(Markdown(agent.status_report()))
                console.print(Markdown(hy["report"]))
            return 0

        if args.command == "seed":
            path = args.file or str(Path(cfg["_paths"]["root"]) / "data" / "contacts" / "sample_crm.json")
            counts = agent.seed_from_file(path)
            console.print(counts)
            return 0

        if args.command == "note":
            text = args.text
            if args.file and not text:
                text = Path(args.file).read_text(encoding="utf-8")
            if not text:
                console.print("[red]Provide --text or --file[/red]")
                return 2
            result = agent.process_note(
                text, use_llm=not args.no_llm, apply=args.apply
            )
            if args.json:
                print(json.dumps(result, indent=2, default=str))
            else:
                console.print(Panel.fit(
                    f"Queued: {len(result['queued'])} · Applied: {len(result['applied'])} · "
                    f"Pending total: {result['pending_count']}",
                    title="Process note",
                ))
                for w in result["queued"]:
                    console.print(f"  [{w['id']}] {w['action']} — {w['reason']}")
            return 0

        if args.command == "pending":
            items = agent.list_pending()
            if args.json:
                print(json.dumps(items, indent=2))
            else:
                if not items:
                    console.print("No pending writes.")
                for w in items:
                    console.print(f"[bold]{w['id']}[/bold] {w['action']} conf={w['confidence']:.2f}")
                    console.print(f"  {w['reason']}")
                    for d in w.get("diffs") or []:
                        console.print(f"  · {d}")
            return 0

        if args.command == "approve":
            if not args.id:
                console.print("[red]--id required[/red]")
                return 2
            r = agent.approve(args.id)
            console.print(r)
            return 0

        if args.command == "reject":
            if not args.id:
                console.print("[red]--id required[/red]")
                return 2
            r = agent.reject(args.id)
            console.print(r)
            return 0

        if args.command == "approve-all":
            r = agent.approve_all()
            console.print(f"Applied {len(r)} writes")
            return 0

        if args.command == "hygiene":
            hy = agent.hygiene()
            if args.json:
                print(json.dumps(hy, indent=2))
            else:
                console.print(Markdown(hy["report"]))
            return 0

        if args.command == "export":
            paths = agent.export()
            console.print(paths)
            return 0

        if args.command == "contact":
            if not args.email:
                console.print("[red]--email required[/red]")
                return 2
            data = {
                "email": args.email,
                "full_name": args.name or "",
                "company_name": args.company or "",
                "title": args.title or "",
            }
            r = agent.upsert_contact_direct(data, approve=args.apply)
            console.print(r)
            return 0

        if args.command == "activity":
            if not args.email or not args.subject:
                console.print("[red]--email and --subject required[/red]")
                return 2
            data = {
                "type": args.act_type,
                "subject": args.subject,
                "body": args.body or "",
                "contact_email": args.email,
                "source": "cli",
            }
            r = agent.log_activity_direct(data, approve=args.apply)
            console.print(r)
            return 0

    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Error:[/red] {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
