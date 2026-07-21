"""CLI entrypoint: python -m src.cli <command>."""

from __future__ import annotations

import argparse
import json
import sys

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from .agent import EmailAssistant
from .config import load_config

console = Console()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="email-assistant",
        description="Matrixly.AI Email Assistant — triage, draft, urgent flags, daily summary",
    )
    parser.add_argument(
        "command",
        choices=["auth", "profile", "triage", "urgent", "draft", "summary"],
        help="Action to run",
    )
    parser.add_argument("--message-id", help="Gmail message id (for draft)")
    parser.add_argument(
        "--no-labels",
        action="store_true",
        help="Do not apply Matrixly/* labels during triage",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Include read messages (not only unread)",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Rule-based only (skip Grok)",
    )
    parser.add_argument(
        "--no-send",
        action="store_true",
        help="For summary: write markdown only, do not email the brief",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=None,
        help="Max messages to process",
    )
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args(argv)

    cfg = load_config()
    agent = EmailAssistant(cfg)

    try:
        if args.command == "auth":
            profile = agent.connect()
            backend = (cfg.get("agent") or {}).get("backend") or "imap"
            mbox_profile = (cfg.get("agent") or {}).get("profile") or "?"
            console.print(
                Panel.fit(
                    f"[bold green]Connected[/bold green]\n"
                    f"Profile: {mbox_profile}\n"
                    f"Backend: {profile.get('backend') or backend}\n"
                    f"Email: {profile.get('emailAddress')}\n"
                    f"Host: {profile.get('imapHost') or 'gmail-api'}\n"
                    f"Messages (inbox): {profile.get('messagesTotal')}",
                    title="Mailbox login",
                )
            )
            return 0

        if args.command == "profile":
            profile = agent.connect()
            if args.json:
                print(json.dumps(profile, indent=2))
            else:
                console.print(profile)
            return 0

        if args.command in {"triage", "urgent"} and args.all:
            agent.cfg.setdefault("triage", {})["unread_only"] = False

        if args.command == "triage":
            result = agent.run(
                "triage",
                apply_labels=not args.no_labels,
                max_results=args.max,
                use_llm=not args.no_llm,
            )
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                console.print(Markdown(result["report"]))
            return 0

        if args.command == "urgent":
            result = agent.run(
                "urgent",
                apply_labels=not args.no_labels,
                max_results=args.max,
                use_llm=not args.no_llm,
            )
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                console.print(Markdown(result["report"]))
            return 0

        if args.command == "draft":
            if not args.message_id:
                console.print("[red]--message-id is required for draft[/red]")
                return 2
            result = agent.run("draft", message_id=args.message_id)
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                console.print(
                    Panel(
                        result["body"],
                        title=f"Draft → {result['to']} · mode={result['mode']} · draft_id={result['draft_id']}",
                    )
                )
            return 0

        if args.command == "summary":
            result = agent.run(
                "summary",
                deliver=not args.no_send,
                apply_labels=not args.no_labels,
                use_llm=not args.no_llm,
            )
            if args.json:
                # avoid huge duplicate in some shells
                slim = {k: v for k, v in result.items() if k != "summary"}
                slim["summary_preview"] = (result.get("summary") or "")[:500]
                print(json.dumps(slim, indent=2))
            else:
                console.print(Markdown(result.get("summary") or ""))
                if result.get("markdown_path"):
                    console.print(f"\n[green]Saved:[/green] {result['markdown_path']}")
                if result.get("sent_message_id"):
                    console.print(
                        f"[green]Emailed brief to[/green] {result.get('delivered_to')} "
                        f"(id {result['sent_message_id']})"
                    )
            return 0

    except FileNotFoundError as exc:
        console.print(f"[red]Setup needed:[/red] {exc}")
        return 1
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Error:[/red] {exc}")
        if args.json:
            print(json.dumps({"error": str(exc)}))
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
