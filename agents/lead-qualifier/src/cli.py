"""CLI: python -m src.cli <command>."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from .agent import LeadQualifier
from .config import load_config
from .models import Lead

console = Console()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="lead-qualifier",
        description="Matrixly.AI Lead Qualifier — score, enrich, outreach, Salesforce export",
    )
    parser.add_argument(
        "command",
        choices=["qualify", "sample", "gmail", "score-one"],
        help="Action to run",
    )
    parser.add_argument("--file", "-f", help="JSON file of leads")
    parser.add_argument("--email", help="Single lead email (score-one)")
    parser.add_argument("--name", help="Single lead name")
    parser.add_argument("--company", help="Single lead company")
    parser.add_argument("--title", help="Single lead title")
    parser.add_argument("--notes", help="Single lead notes / inquiry text")
    parser.add_argument("--no-llm", action="store_true", help="Heuristic only")
    parser.add_argument("--no-export", action="store_true", help="Skip Salesforce file export")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args(argv)

    cfg = load_config()
    agent = LeadQualifier(cfg)
    use_llm = not args.no_llm
    export = not args.no_export

    try:
        if args.command == "sample":
            result = agent.run("sample", use_llm=use_llm, export=export)
        elif args.command == "gmail":
            result = agent.run("gmail", use_llm=use_llm, export=export)
        elif args.command == "score-one":
            if not args.email:
                console.print("[red]--email required for score-one[/red]")
                return 2
            lead = Lead(
                email=args.email,
                full_name=args.name or "",
                company=args.company or "",
                title=args.title or "",
                notes=args.notes or "",
                source="CLI",
            )
            result = agent.run("qualify", leads=[lead], use_llm=use_llm, export=export)
        else:  # qualify
            if not args.file:
                console.print("[red]--file required for qualify (or use sample / gmail)[/red]")
                return 2
            result = agent.run("qualify", path=args.file, use_llm=use_llm, export=export)

        if args.json:
            print(json.dumps({k: v for k, v in result.items() if k != "report"}, indent=2))
            if result.get("report"):
                print(result["report"], file=sys.stderr)
        else:
            console.print(Markdown(result.get("report") or "_No report_"))
            if result.get("salesforce_export"):
                paths = result["salesforce_export"]
                console.print(
                    Panel.fit(
                        f"JSON: {paths.get('json')}\nCSV:  {paths.get('csv')}",
                        title="Salesforce export",
                    )
                )
            # Show first sequence sample
            results = result.get("results") or []
            for q in results[:1]:
                seq = q.get("sequence") or []
                if seq:
                    t0 = seq[0]
                    console.print(
                        Panel(
                            t0.get("body") or "",
                            title=f"Sample outreach · Day {t0.get('day')} · {t0.get('subject')}",
                        )
                    )
        return 0
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Error:[/red] {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
