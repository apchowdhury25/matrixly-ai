"""CLI for Starter Pack."""

from __future__ import annotations

import argparse
import json

from rich.console import Console
from rich.panel import Panel

from .config import load_config
from .pack import StarterPack

console = Console()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="starter-pack")
    p.add_argument(
        "command",
        choices=["status", "overview", "serve"],
    )
    p.add_argument("--json", action="store_true")
    p.add_argument("--host", default=None)
    p.add_argument("--port", type=int, default=None)
    args = p.parse_args(argv)

    cfg = load_config()
    pack = StarterPack(cfg)

    if args.command == "status":
        st = pack.status()
        print(json.dumps(st, indent=2) if args.json else Panel.fit(json.dumps(st, indent=2), title="Starter Pack"))
        return 0

    if args.command == "overview":
        ov = pack.overview()
        if args.json:
            print(json.dumps(ov.model_dump(), indent=2))
        else:
            console.print(f"[bold]{ov.pack}[/bold] v{ov.version}")
            for a in ov.agents:
                state = "online" if a.online else ("disabled" if not a.enabled else "offline")
                console.print(f"  • {a.name}: {state} — {a.metrics}")
            console.print(f"Analytics: {ov.analytics}")
        return 0

    if args.command == "serve":
        import uvicorn

        host = args.host or (cfg.get("server") or {}).get("host") or "0.0.0.0"
        port = args.port or int((cfg.get("server") or {}).get("port") or 8800)
        uvicorn.run("src.main:app", host=host, port=port, reload=False)
        return 0

    return 1
