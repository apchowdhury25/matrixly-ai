"""CLI for SEO-Bespoke."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from .config import load_config
from .models import QuizAnswers
from .orchestrator import SEOBespoke

# Prefer UTF-8 on Windows consoles; fall back to safe ASCII-friendly output.
try:
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

console = Console(legacy_windows=False)


def _interactive_quiz() -> QuizAnswers:
    console.print(Panel.fit(
        "[bold cyan]SEO-Bespoke Business Quiz[/bold cyan]\n"
        "Six short steps. Answers become your custom SEO agent.",
        title="Matrixly",
    ))

    console.print("\n[bold]1/6 Domain & website[/bold]")
    domain = Prompt.ask("Website domain (e.g. apexcomfort.com)", default="")
    website = Prompt.ask("Full website URL", default=f"https://{domain}" if domain else "")
    has_gbp = Confirm.ask("Do you have a Google Business Profile?", default=True)
    has_blog = Confirm.ask("Do you have a blog?", default=False)
    cms = Prompt.ask("Website platform", default="wordpress", choices=["wordpress", "shopify", "squarespace", "wix", "custom", "unknown"])

    console.print("\n[bold]2/6 Industry & niche[/bold]")
    industry = Prompt.ask("Industry", default="Home services")
    niche = Prompt.ask("Niche (more specific)", default="")
    sub = Prompt.ask("Sub-niches (comma-separated)", default="")

    console.print("\n[bold]3/6 Business[/bold]")
    bname = Prompt.ask("Business name")
    desc = Prompt.ask("What do you do? (1-3 sentences)")
    uv = Prompt.ask("What makes you different?")
    services = Prompt.ask("Main services/products (comma-separated)", default="")

    console.print("\n[bold]4/6 Customers[/bold]")
    persona = Prompt.ask("Who is your ideal customer?")
    pains = Prompt.ask("Their main pain points (comma-separated)", default="")

    console.print("\n[bold]5/6 Location[/bold]")
    city = Prompt.ask("Primary city", default="")
    region = Prompt.ask("State / region", default="")
    areas = Prompt.ask("Service areas (comma-separated)", default=f"{city}, {region}".strip(", "))

    console.print("\n[bold]6/6 Goals[/bold]")
    maturity = Prompt.ask(
        "SEO maturity",
        default="basic",
        choices=["none", "basic", "intermediate", "advanced"],
    )
    goal = Prompt.ask(
        "Primary goal",
        default="near_me_leads",
        choices=[
            "near_me_leads",
            "organic_leads",
            "ecommerce",
            "brand_authority",
            "local_dominance",
            "content_engine",
        ],
    )
    metric = Prompt.ask("How will you measure success?", default="more qualified inquiries")

    def split(s: str) -> list[str]:
        return [x.strip() for x in s.split(",") if x.strip()]

    return QuizAnswers(
        domain={
            "domain": domain,
            "website_url": website,
            "has_gbp": has_gbp,
            "has_blog": has_blog,
            "cms": cms,
        },
        industry={
            "industry": industry,
            "niche": niche or industry,
            "sub_niches": split(sub),
        },
        business={
            "business_name": bname,
            "description": desc,
            "unique_value": uv,
            "products_services": split(services),
        },
        customers={
            "primary_persona": persona,
            "pain_points": split(pains),
        },
        location={
            "primary_city": city,
            "primary_region": region,
            "service_areas": split(areas),
        },
        goals={
            "maturity": maturity,
            "primary_goal": goal,
            "success_metric": metric,
            "timeline_days": 90,
        },
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="seo-bespoke")
    p.add_argument(
        "command",
        choices=[
            "status",
            "graph",
            "demo",
            "quiz",
            "generate",
            "regenerate",
            "runs",
            "profiles",
            "packages",
            "pending",
            "approve",
            "reject",
            "keywords",
            "roi",
            "chat",
            "serve",
        ],
    )
    p.add_argument("path", nargs="?", help="JSON quiz file for generate")
    p.add_argument("--id", help="HITL, run, or profile id")
    p.add_argument("--text", help="Chat message")
    p.add_argument("--json", action="store_true")
    p.add_argument("--host", default=None)
    p.add_argument("--port", type=int, default=None)
    args = p.parse_args(argv)

    cfg = load_config()
    agent = SEOBespoke(cfg)

    if args.command == "status":
        st = agent.status()
        if args.json:
            print(json.dumps(st, indent=2))
        else:
            console.print(Panel.fit(json.dumps(st, indent=2), title="SEO-Bespoke"))
        return 0

    if args.command == "graph":
        print(json.dumps(agent.graph_describe(), indent=2))
        return 0

    if args.command == "demo":
        console.print("[cyan]Running demo pipeline (Apex Comfort HVAC)...[/cyan]")
        run = agent.demo()
        console.print(
            f"[green]run={run.id} status={run.status.value} "
            f"profile={(run.profile.business_name if run.profile else 'n/a')} "
            f"package={run.package_path}[/green]"
        )
        if run.profile and not args.json:
            console.print(Panel(run.profile.summary_markdown[:2000], title="Profile preview"))
        if args.json:
            print(json.dumps({"id": run.id, "status": run.status.value, "package": run.package}, indent=2))
        return 0

    if args.command == "quiz":
        answers = _interactive_quiz()
        console.print("[cyan]Running parallel graph (20 nodes)...[/cyan]")
        run = agent.run_full_pipeline(answers)
        console.print(
            f"[green]Done. run={run.id} status={run.status.value}\n"
            f"Profile: {run.profile_path}\nPackage: {run.package_path}\nHITL: {run.hitl_id}[/green]"
        )
        return 0

    if args.command == "generate":
        if not args.path:
            console.print("[red]JSON quiz path required (or use quiz / demo)[/red]")
            return 1
        data = json.loads(Path(args.path).read_text(encoding="utf-8"))
        run = agent.run_full_pipeline(QuizAnswers(**data))
        print(json.dumps({"id": run.id, "status": run.status.value, "package_path": run.package_path}, indent=2))
        return 0

    if args.command == "regenerate":
        if not args.id:
            console.print("[red]--id profile_id required[/red]")
            return 1
        run = agent.regenerate_from_profile(args.id)
        print(json.dumps({"id": run.id, "status": run.status.value, "package_path": run.package_path}, indent=2))
        return 0

    if args.command == "runs":
        items = agent.list_runs()
        print(json.dumps([{"id": r.id, "status": r.status.value, "package": r.package_path} for r in items], indent=2))
        return 0

    if args.command == "profiles":
        items = agent.list_profiles()
        print(json.dumps([{"id": p.id, "name": p.business_name, "goal": p.primary_goal} for p in items], indent=2))
        return 0

    if args.command == "packages":
        print(json.dumps(agent.packages.list(), indent=2))
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

    if args.command == "keywords":
        print(json.dumps({"summary": agent.keywords.summary(), "items": [k.model_dump() for k in agent.keywords.list()]}, indent=2))
        return 0

    if args.command == "roi":
        print(json.dumps(agent.roi.summary(), indent=2))
        return 0

    if args.command == "chat":
        msg = args.text or Prompt.ask("You")
        out = agent.chat(msg)
        console.print(Panel(out["reply"], title="SEO-Bespoke"))
        return 0

    if args.command == "serve":
        import uvicorn

        host = args.host or (cfg.get("server") or {}).get("host") or "0.0.0.0"
        port = args.port or int((cfg.get("server") or {}).get("port") or 8801)
        console.print(f"[green]SEO-Bespoke dashboard -> http://127.0.0.1:{port}/[/green]")
        uvicorn.run("src.main:app", host=host, port=port, reload=False)
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
