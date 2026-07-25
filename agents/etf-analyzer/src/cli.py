"""CLI for ETF Analyzer."""

from __future__ import annotations

import argparse
import json

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from .config import load_config
from .orchestrator import ETFAnalyzer

console = Console()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="etf-analyzer")
    p.add_argument("command", choices=["status", "analyze", "chat", "serve"])
    p.add_argument("ticker", nargs="?", default="", help="ETF ticker")
    p.add_argument("--message", default="", help="Chat message")
    p.add_argument("--notion", action="store_true")
    p.add_argument("--json", action="store_true")
    p.add_argument("--host", default=None)
    p.add_argument("--port", type=int, default=None)
    args = p.parse_args(argv)

    cfg = load_config()
    agent = ETFAnalyzer(cfg)

    if args.command == "status":
        st = agent.status()
        print(json.dumps(st, indent=2) if args.json else Panel.fit(json.dumps(st, indent=2), title="ETF Analyzer"))
        return 0

    if args.command == "analyze":
        report = agent.analyze(args.ticker, save_to_notion=args.notion)
        if args.json:
            print(json.dumps(report.model_dump(), indent=2))
        else:
            console.print(Markdown(report.markdown))
        return 0

    if args.command == "chat":
        msg = args.message or args.ticker or ""
        resp = agent.chat(msg)
        if args.json:
            print(json.dumps(resp.model_dump(), indent=2))
        else:
            console.print(Markdown(resp.reply))
        return 0

    if args.command == "serve":
        import uvicorn

        host = args.host or (cfg.get("server") or {}).get("host") or "0.0.0.0"
        port = args.port or int((cfg.get("server") or {}).get("port") or 8797)
        uvicorn.run("src.main:app", host=host, port=port, reload=False)
        return 0

    return 1
