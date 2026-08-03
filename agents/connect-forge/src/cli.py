"""CLI for ConnectForge — ASCII-safe for Windows consoles."""

from __future__ import annotations

import argparse
import json
import sys

from rich.console import Console
from rich.panel import Panel

from .config import load_config
from .orchestrator import ConnectForge

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

console = Console(legacy_windows=False)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="connect-forge")
    p.add_argument(
        "command",
        choices=[
            "status",
            "demo",
            "send",
            "conversation",
            "messages",
            "pending",
            "approve",
            "reject",
            "call",
            "serve",
        ],
    )
    p.add_argument("--to", default="", help="Destination E.164 number")
    p.add_argument("--body", default="", help="SMS body")
    p.add_argument("--id", default="", help="HITL id")
    p.add_argument("--say", default="", help="Voice say text")
    p.add_argument("--host", default=None)
    p.add_argument("--port", type=int, default=None)
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    cfg = load_config()
    agent = ConnectForge(cfg)

    if args.command == "status":
        st = agent.status()
        if args.json:
            print(json.dumps(st, indent=2))
        else:
            console.print(Panel.fit(json.dumps(st, indent=2), title="ConnectForge"))
        return 0

    if args.command == "demo":
        out = agent.demo()
        if args.json:
            print(json.dumps(out, indent=2))
        else:
            console.print(Panel.fit(json.dumps(out, indent=2), title="Demo"))
            console.print("[green]Demo complete (mock Twilio if no credentials).[/green]")
        return 0

    if args.command == "send":
        if not args.to or not args.body:
            console.print("[red]--to and --body required[/red]")
            return 1
        print(json.dumps(agent.send_sms(args.to, args.body), indent=2))
        return 0

    if args.command == "conversation":
        if not args.to:
            console.print("[red]--to required[/red]")
            return 1
        body = args.body or "Hi! Thanks for contacting us. How can we help today?"
        print(json.dumps(agent.start_conversation(args.to, body), indent=2))
        return 0

    if args.command == "messages":
        items = [m.model_dump() for m in agent.store.list_messages()]
        print(json.dumps(items, indent=2))
        return 0

    if args.command == "pending":
        print(json.dumps([a.model_dump() for a in agent.hitl.list_pending()], indent=2))
        return 0

    if args.command == "approve":
        if not args.id:
            console.print("[red]--id hitl_id required[/red]")
            return 1
        print(json.dumps(agent.approve_hitl(args.id), indent=2))
        return 0

    if args.command == "reject":
        if not args.id:
            console.print("[red]--id hitl_id required[/red]")
            return 1
        print(json.dumps(agent.reject_hitl(args.id), indent=2))
        return 0

    if args.command == "call":
        if not args.to:
            console.print("[red]--to required[/red]")
            return 1
        print(json.dumps(agent.start_call(args.to, say=args.say or None), indent=2))
        return 0

    if args.command == "serve":
        import uvicorn

        host = args.host or (cfg.get("server") or {}).get("host") or "0.0.0.0"
        port = args.port or int((cfg.get("server") or {}).get("port") or 8802)
        console.print(f"[green]ConnectForge dashboard -> http://127.0.0.1:{port}/[/green]")
        uvicorn.run("src.main:app", host=host, port=port, reload=False)
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
