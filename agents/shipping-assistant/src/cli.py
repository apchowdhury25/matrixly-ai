"""CLI: python -m src.cli <command>."""

from __future__ import annotations

import argparse
import json
import sys

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from .agent import ShippingAssistant
from .config import load_config

console = Console()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="shipping-assistant",
        description="Matrixly Shipping Assistant — ShipStation track, exceptions, WISMO drafts, HITL",
    )
    p.add_argument(
        "command",
        choices=[
            "status",
            "list",
            "track",
            "exceptions",
            "wismo",
            "notify-drafts",
            "pending",
            "propose-cancel",
            "approve",
            "reject",
            "export",
            "demo",
        ],
    )
    p.add_argument("--order", help="Order number")
    p.add_argument("--tracking", help="Tracking number")
    p.add_argument("--id", help="Pending action id")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    cfg = load_config()
    agent = ShippingAssistant(cfg)

    try:
        if args.command == "status":
            st = agent.status()
            if args.json:
                print(json.dumps(st, indent=2))
            else:
                console.print(Panel.fit(
                    f"Mode: {st['mode']}\nPending HITL actions: {st['pending_actions']}",
                    title="Shipping Assistant",
                ))
            return 0

        if args.command in {"list", "demo"}:
            ships = agent.list_shipments()
            if args.json:
                print(json.dumps([s.to_dict() for s in ships], indent=2))
            else:
                console.print(Markdown(agent.shipments_report(ships)))
                if args.command == "demo":
                    ex = agent.exceptions()
                    console.print(Markdown(ex["report"]))
            return 0

        if args.command == "track":
            s = agent.track(order_number=args.order or "", tracking=args.tracking or "")
            if not s:
                console.print("[red]Not found[/red]")
                return 1
            if args.json:
                print(json.dumps(s.to_dict(), indent=2))
            else:
                console.print(s.to_dict())
            return 0

        if args.command == "exceptions":
            ex = agent.exceptions()
            if args.json:
                print(json.dumps(ex, indent=2))
            else:
                console.print(Markdown(ex["report"]))
            return 0

        if args.command == "wismo":
            if not args.order:
                console.print("[red]--order required[/red]")
                return 2
            result = agent.wismo(args.order)
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                d = result["draft"]
                console.print(Panel(d["body"], title=f"WISMO draft · {d['subject']}"))
            return 0

        if args.command == "notify-drafts":
            drafts = agent.notify_drafts_for_exceptions()
            if args.json:
                print(json.dumps(drafts, indent=2))
            else:
                console.print(f"{len(drafts)} exception notification draft(s)")
                for d in drafts:
                    console.print(f"\n[bold]{d['order_number']}[/bold]")
                    console.print(f"  Internal → {d['internal_draft']['to']}: {d['internal_draft']['subject']}")
                    console.print(f"  Customer draft subject: {d['customer_draft']['subject']}")
            return 0

        if args.command == "pending":
            items = agent.list_pending()
            if args.json:
                print(json.dumps(items, indent=2))
            else:
                if not items:
                    console.print("No pending actions.")
                for i in items:
                    console.print(f"{i['id']} · {i['action']} · {i['reason']}")
            return 0

        if args.command == "propose-cancel":
            if not args.order:
                console.print("[red]--order required[/red]")
                return 2
            pa = agent.propose_action(
                "cancel_order",
                {"order_number": args.order},
                reason=f"Cancel request for {args.order}",
            )
            console.print(pa.to_dict())
            return 0

        if args.command == "approve":
            if not args.id:
                console.print("[red]--id required[/red]")
                return 2
            console.print(agent.approve(args.id))
            return 0

        if args.command == "reject":
            if not args.id:
                console.print("[red]--id required[/red]")
                return 2
            console.print(agent.reject(args.id))
            return 0

        if args.command == "export":
            path = agent.export_snapshot()
            console.print(f"Wrote {path}")
            return 0

    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Error:[/red] {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
