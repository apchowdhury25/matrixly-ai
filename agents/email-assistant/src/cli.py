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
from .gmail_client import GmailAuthError

console = Console()

PRIVACY_LINE = (
    "Your emails never leave your control. We do not train on them. "
    "You can revoke access any time in your Google account."
)


def _cmd_connect_gmail(agent: EmailAssistant, args: argparse.Namespace) -> int:
    console.print(
        Panel.fit(
            "[bold]Connect your Gmail[/bold]\n\n"
            "So your AI assistant can keep your inbox under control while you run the business.\n\n"
            "What happens next:\n"
            "  1. Your browser opens Google's sign-in page\n"
            "  2. You approve access (read, labels, drafts, send self-briefs)\n"
            "  3. Matrixly saves a secure login token on this computer only\n\n"
            f"[dim]{PRIVACY_LINE}[/dim]\n\n"
            "[yellow]Important:[/yellow] Replies are [bold]drafts only[/bold] — "
            "nothing is sent to customers until you hit Send.",
            title="Matrixly Email Assistant",
            border_style="cyan",
        )
    )
    try:
        profile = agent.connect_gmail(force=bool(args.force))
    except FileNotFoundError as exc:
        console.print(f"[red]Setup needed:[/red]\n{exc}")
        return 1
    except GmailAuthError as exc:
        console.print(f"[red]Could not connect Gmail:[/red]\n{exc}")
        return 1
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Error:[/red] {exc}")
        return 1

    labels = profile.get("matrixly_labels") or []
    email = profile.get("emailAddress") or "?"
    console.print(
        Panel.fit(
            f"[bold green]Success — Gmail connected[/bold green]\n\n"
            f"Mailbox: [bold]{email}[/bold]\n"
            f"Messages in mailbox: {profile.get('messagesTotal', '?')}\n"
            f"Matrixly labels ready: {', '.join(labels) if labels else '(created on first triage)'}\n\n"
            "Next steps:\n"
            "  python -m src.cli profile\n"
            "  python -m src.cli triage\n"
            "  python -m src.cli impact\n\n"
            f"[dim]{PRIVACY_LINE}[/dim]",
            title="You're all set",
            border_style="green",
        )
    )
    if args.json:
        safe = {
            "emailAddress": email,
            "messagesTotal": profile.get("messagesTotal"),
            "matrixly_labels": labels,
            "backend": "gmail",
            "token_valid": (profile.get("token_status") or {}).get("valid"),
        }
        print(json.dumps(safe, indent=2))
    return 0


def _cmd_test_mode(agent: EmailAssistant, args: argparse.Namespace) -> int:
    console.print(
        Panel.fit(
            "[bold]Test Mode[/bold] — sample inbox, no real email connected.\n"
            "Perfect for seeing triage, labels, drafts, and your impact report first.",
            border_style="cyan",
        )
    )
    demo = EmailAssistant(agent.cfg, test_mode=True)
    result = demo.run("test-mode", use_llm=not args.no_llm)
    if args.json:
        print(json.dumps({k: v for k, v in result.items() if k != "impact_report"}, indent=2))
        return 0
    console.print(Markdown(result["report"]))
    if result.get("impact_report"):
        console.print()
        console.print(Markdown(result["impact_report"]))
    if result.get("impact_path"):
        console.print(f"\n[green]Impact report saved:[/green] {result['impact_path']}")
        console.print("[dim]Screenshot that file or the terminal for your demo video.[/dim]")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="email-assistant",
        description=(
            "Matrixly Email Assistant — connect Gmail, triage, draft (never auto-send), "
            "daily brief, Test Mode for SMBs"
        ),
    )
    parser.add_argument(
        "command",
        choices=[
            "auth",
            "connect-gmail",
            "profile",
            "triage",
            "urgent",
            "draft",
            "summary",
            "impact",
            "test-mode",
            "token-status",
        ],
        help="Action to run",
    )
    parser.add_argument("--message-id", help="Message id (for draft)")
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
    parser.add_argument(
        "--test",
        action="store_true",
        help="Use Test Mode sample inbox (no real mail)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="For connect-gmail: discard saved token and re-authenticate",
    )
    parser.add_argument(
        "--no-impact",
        action="store_true",
        help="Skip auto 24h impact report after triage",
    )
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args(argv)

    cfg = load_config()
    if args.test or args.command == "test-mode":
        cfg.setdefault("agent", {})["backend"] = "test"
    # connect-gmail always uses Gmail API
    if args.command == "connect-gmail":
        cfg.setdefault("agent", {})["backend"] = "gmail"
        cfg["agent"]["profile"] = "gmail"

    agent = EmailAssistant(cfg, test_mode=bool(args.test or args.command == "test-mode"))

    try:
        if args.command == "connect-gmail":
            return _cmd_connect_gmail(agent, args)

        if args.command == "test-mode":
            return _cmd_test_mode(agent, args)

        if args.command == "token-status":
            status = agent.token_status()
            if args.json:
                print(json.dumps(status, indent=2))
            else:
                console.print(status)
                if status.get("valid"):
                    console.print("[green]Token is valid (refresh works if expired).[/green]")
                elif status.get("token_file_exists"):
                    console.print(
                        "[yellow]Token present but not valid — run connect-gmail --force[/yellow]"
                    )
                else:
                    console.print("[yellow]No token — run connect-gmail[/yellow]")
            return 0 if status.get("valid") or args.test else 1

        if args.command == "auth":
            # auth = connect current backend (Gmail OAuth or IMAP login)
            if (cfg.get("agent") or {}).get("backend") == "gmail":
                return _cmd_connect_gmail(agent, args)
            profile = agent.connect()
            backend = (cfg.get("agent") or {}).get("backend") or "imap"
            mbox_profile = (cfg.get("agent") or {}).get("profile") or "?"
            console.print(
                Panel.fit(
                    f"[bold green]Connected[/bold green]\n"
                    f"Profile: {mbox_profile}\n"
                    f"Backend: {profile.get('backend') or backend}\n"
                    f"Email: {profile.get('emailAddress')}\n"
                    f"Host: {profile.get('imapHost') or '—'}\n"
                    f"Messages (inbox): {profile.get('messagesTotal')}",
                    title="Mailbox login",
                )
            )
            return 0

        if args.command == "profile":
            profile = agent.connect()
            if args.json:
                print(json.dumps(profile, indent=2, default=str))
            else:
                console.print(
                    Panel.fit(
                        f"Email: [bold]{profile.get('emailAddress')}[/bold]\n"
                        f"Backend: {profile.get('backend') or (cfg.get('agent') or {}).get('backend')}\n"
                        f"Messages: {profile.get('messagesTotal')}\n"
                        f"Test mode: {bool(profile.get('testMode'))}",
                        title="Mailbox profile",
                    )
                )
            return 0

        if args.command in {"triage", "urgent"} and args.all:
            agent.cfg.setdefault("triage", {})["unread_only"] = False

        if args.command == "triage":
            result = agent.run(
                "triage",
                apply_labels=not args.no_labels,
                max_results=args.max,
                use_llm=not args.no_llm,
                impact=not args.no_impact,
            )
            if args.json:
                print(json.dumps({k: v for k, v in result.items() if k != "impact_report"}, indent=2))
            else:
                console.print(Markdown(result["report"]))
                if result.get("impact_path"):
                    console.print(
                        f"\n[green]Your first 24-hour impact report:[/green] {result['impact_path']}"
                    )
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
                console.print(
                    "[dim]Tip: run triage --json to copy an id, or use Test Mode ids like sample-quote-request[/dim]"
                )
                return 2
            result = agent.run("draft", message_id=args.message_id)
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                console.print(
                    Panel(
                        result["body"],
                        title=(
                            f"Draft → {result['to']} · mode={result['mode']} · "
                            f"draft_id={result['draft_id']} · [yellow]not sent[/yellow]"
                        ),
                    )
                )
                console.print(
                    "[dim]Human-in-the-loop: open Gmail Drafts (or IMAP Drafts) to review and send.[/dim]"
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

        if args.command == "impact":
            result = agent.run(
                "impact",
                apply_labels=not args.no_labels,
                use_llm=not args.no_llm,
            )
            if args.json:
                print(
                    json.dumps(
                        {
                            "markdown_path": result.get("markdown_path"),
                            "items_count": len(result.get("items") or []),
                        },
                        indent=2,
                    )
                )
            else:
                console.print(Markdown(result.get("report") or ""))
                if result.get("markdown_path"):
                    console.print(f"\n[green]Saved for screenshot:[/green] {result['markdown_path']}")
            return 0

    except FileNotFoundError as exc:
        console.print(f"[red]Setup needed:[/red] {exc}")
        return 1
    except GmailAuthError as exc:
        console.print(f"[red]Gmail auth:[/red] {exc}")
        return 1
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Error:[/red] {exc}")
        if args.json:
            print(json.dumps({"error": str(exc)}))
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
