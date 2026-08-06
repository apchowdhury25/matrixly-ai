#!/usr/bin/env python3
"""
ContentForge one-command setup for non-technical business owners.

Runs venv → install → .env → brand voice → smoke test → optional server.
Only prompts for business details and optional secrets (never internal keys).

Usage (from agents/content-forge):
  python scripts/bootstrap.py
  python scripts/bootstrap.py --yes          # defaults, minimal prompts
  python scripts/bootstrap.py --no-serve     # install only
  python scripts/bootstrap.py --skip-smoke
"""

from __future__ import annotations

import argparse
import os
import secrets
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent.parent
VENV_DIR = ROOT / ".venv"
ENV_PATH = ROOT / ".env"
ENV_EXAMPLE = ROOT / ".env.example"
VOICE_PATH = ROOT / "brand" / "voice.md"
REQUIREMENTS = ROOT / "requirements.txt"
HEALTH_URL = "http://127.0.0.1:8792/v1/health"
WORKSPACE_URL = "http://127.0.0.1:8792/static/workspace/index.html"
DEFAULT_PORT = 8792

PRIVACY = (
    "Your content stays on this computer unless you connect WordPress/Buffer. "
    "Nothing is published to customers until you approve it."
)


# ─── output helpers (no third-party deps before install) ─────────────────────

def _ok(msg: str) -> None:
    print(f"  ✓  {msg}")


def _info(msg: str) -> None:
    print(f"  →  {msg}")


def _warn(msg: str) -> None:
    print(f"  !  {msg}")


def _err(msg: str) -> None:
    print(f"  ✗  {msg}", file=sys.stderr)


def _banner() -> None:
    print()
    print("=" * 60)
    print("  Matrixly · Content desk setup")
    print("  Turn one article into posts, email, and ads.")
    print("=" * 60)
    print()
    print(f"  {PRIVACY}")
    print()


def _prompt(label: str, *, default: str = "", secret: bool = False) -> str:
    hint = f" [{default}]" if default else ""
    if secret:
        try:
            import getpass

            raw = getpass.getpass(f"  {label}{hint}: ").strip()
        except Exception:  # noqa: BLE001
            raw = input(f"  {label}{hint}: ").strip()
    else:
        raw = input(f"  {label}{hint}: ").strip()
    return raw if raw else default


def _prompt_yes_no(label: str, *, default: bool = True) -> bool:
    d = "Y/n" if default else "y/N"
    raw = input(f"  {label} [{d}]: ").strip().lower()
    if not raw:
        return default
    return raw in {"y", "yes"}


def _prompt_choice(label: str, options: list[tuple[str, str]], default: str) -> str:
    print(f"  {label}")
    for i, (oid, desc) in enumerate(options, 1):
        mark = " (recommended)" if oid == default else ""
        print(f"     {i}. {desc}{mark}")
    while True:
        raw = input(f"  Choose 1–{len(options)} [{default}]: ").strip()
        if not raw:
            return default
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1][0]
        for oid, _ in options:
            if raw.lower() == oid.lower():
                return oid
        print("  Please enter a number from the list.")


# ─── python / venv ───────────────────────────────────────────────────────────

def _venv_python() -> Path:
    if sys.platform == "win32":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def _ensure_python() -> None:
    if sys.version_info < (3, 10):
        _err(f"Python 3.10+ is required (you have {sys.version.split()[0]}).")
        _info("Install from https://www.python.org/downloads/ and re-run this setup.")
        raise SystemExit(1)
    _ok(f"Python {sys.version.split()[0]}")


def _ensure_venv() -> Path:
    py = _venv_python()
    if py.is_file():
        _ok("Virtual environment ready")
        return py
    _info("Creating a private workspace for this desk (one-time)…")
    subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)], check=True, cwd=str(ROOT))
    if not _venv_python().is_file():
        _err("Could not create virtual environment.")
        raise SystemExit(1)
    _ok("Virtual environment created")
    return _venv_python()


def _pip_install(py: Path) -> None:
    _info("Installing Content desk software (may take 1–2 minutes)…")
    subprocess.run(
        [str(py), "-m", "pip", "install", "--upgrade", "pip", "wheel"],
        check=True,
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )
    r = subprocess.run(
        [str(py), "-m", "pip", "install", "-r", str(REQUIREMENTS)],
        cwd=str(ROOT),
    )
    if r.returncode != 0:
        _err("Install failed. Check your internet connection and try again.")
        raise SystemExit(1)
    _ok("Software installed")


# ─── env / brand ─────────────────────────────────────────────────────────────

def _gen_key(prefix: str, nbytes: int = 18) -> str:
    return prefix + secrets.token_urlsafe(nbytes)


def _load_env_example() -> dict[str, str]:
    out: dict[str, str] = {}
    if not ENV_EXAMPLE.is_file():
        return out
    for line in ENV_EXAMPLE.read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, _, v = s.partition("=")
        out[k.strip()] = v.strip()
    return out


def _write_env(values: dict[str, str]) -> None:
    # Preserve comments from example where possible; write key=value block
    lines: list[str] = [
        "# ContentForge · generated by scripts/bootstrap.py",
        "# Do not commit this file. Do not paste secrets into chat.",
        "",
    ]
    base = _load_env_example()
    base.update(values)
    # Preferred order
    order = [
        "XAI_API_KEY",
        "XAI_MODEL",
        "XAI_BASE_URL",
        "CONTENTFORGE_API_KEY",
        "CONTENTFORGE_WIDGET_KEY",
        "CORS_ORIGINS",
        "HITL_MODE",
        "HITL_AUTO_APPROVE",
        "BUSINESS_NAME",
        "SUPPORT_EMAIL",
        "TIMEZONE",
        "PUBLISH_BACKEND",
        "BUFFER_ACCESS_TOKEN",
        "BUFFER_PROFILE_IDS",
        "HOOTSUITE_ACCESS_TOKEN",
        "WORDPRESS_SITE_URL",
        "WORDPRESS_USERNAME",
        "WORDPRESS_APP_PASSWORD",
        "COST_INPUT_PER_1M",
        "COST_OUTPUT_PER_1M",
    ]
    seen: set[str] = set()
    for k in order:
        if k in base:
            lines.append(f"{k}={base[k]}")
            seen.add(k)
    for k, v in sorted(base.items()):
        if k not in seen:
            lines.append(f"{k}={v}")
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        ENV_PATH.chmod(0o600)
    except OSError:
        pass
    _ok(f"Saved settings to {ENV_PATH.name} (private on this computer)")


def _write_brand_voice(
    *,
    business_name: str,
    website: str,
    voice_notes: str,
) -> None:
    VOICE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if voice_notes.strip():
        body = (
            f"# Brand voice — {business_name}\n\n"
            f"## Who we are\n"
            f"{business_name}"
            + (f" ({website})" if website else "")
            + ".\n\n"
            f"## How we write (from the owner)\n"
            f"{voice_notes.strip()}\n\n"
            f"## Tone\n"
            f"- Clear and concrete\n"
            f"- Professional but approachable\n"
            f"- Trust-first — no empty hype\n\n"
            f"## Content principles\n"
            f"1. Lead with the problem the reader feels\n"
            f"2. Show a simple path\n"
            f"3. End with a clear next action\n"
            f"4. Nothing customer-facing publishes without human approval\n"
        )
    else:
        site_line = f" Website: {website}." if website else ""
        body = (
            f"# Brand voice — {business_name}\n\n"
            f"## Who we are\n"
            f"{business_name} is a small business that serves customers with practical, "
            f"trustworthy content.{site_line}\n\n"
            f"## Tone\n"
            f"- **Professional but approachable** — expert without arrogance\n"
            f"- **Clear and concrete** — prefer examples and outcomes over buzzwords\n"
            f"- **Optimistic and practical** — focus on what operators can do this week\n"
            f"- **Trust-first** — never promise magic; emphasize review and ROI\n\n"
            f"## Vocabulary to prefer\n"
            f"- clear outcomes, customers, drafts, review, schedule\n\n"
            f"## Vocabulary to avoid\n"
            f"- Revolutionary, disrupt, guaranteed 10x without evidence\n"
            f"- Unexplained acronyms\n\n"
            f"## Audience\n"
            f"Customers and prospects of {business_name}.\n\n"
            f"## Content principles\n"
            f"1. Lead with the problem the reader feels\n"
            f"2. Show a simple path (3 steps max in social)\n"
            f"3. End with a clear next action\n"
            f"4. Keep SEO natural — keywords serve the reader\n"
        )
    VOICE_PATH.write_text(body, encoding="utf-8")
    _ok("Saved your writing style for the Content desk")


def _collect_answers(*, assume_yes: bool) -> dict[str, str]:
    print("─" * 60)
    print("  About your business")
    print("─" * 60)
    print()

    if assume_yes:
        business = "My Business"
        website = ""
        email = ""
        voice = ""
        publish = "local"
        xai = ""
        wp_url = wp_user = wp_pass = ""
        _info("Using safe defaults (--yes). Edit .env or re-run without --yes to customize.")
    else:
        business = _prompt("What's your business called?", default="My Business")
        website = _prompt("Your website (optional)")
        email = _prompt("Best email for content questions (optional)")
        print()
        print("  How do you usually write? (tone, words you use, words to avoid)")
        print("  Press Enter twice on an empty line when done — or Enter once to skip.")
        lines: list[str] = []
        while True:
            try:
                line = input("  | ")
            except EOFError:
                break
            if line == "" and (not lines or lines[-1] == ""):
                break
            lines.append(line)
        # drop trailing empty
        while lines and lines[-1] == "":
            lines.pop()
        voice = "\n".join(lines).strip()
        print()
        xai = _prompt(
            "xAI API key for smarter writing (optional — leave blank for free drafts)",
            secret=True,
        )
        print()
        publish = _prompt_choice(
            "Where should finished drafts go?",
            [
                ("local", "Save on this computer only (safest start)"),
                ("wordpress", "WordPress as drafts (you still approve)"),
                ("buffer", "Buffer (you'll add the token later)"),
            ],
            "local",
        )
        wp_url = wp_user = wp_pass = ""
        if publish == "wordpress":
            print()
            _info("WordPress: use an Application Password, not your normal login.")
            wp_url = _prompt("WordPress site URL (https://…)", default="")
            wp_user = _prompt("WordPress username")
            wp_pass = _prompt("Application password", secret=True)

    values = _load_env_example()
    values["BUSINESS_NAME"] = business
    if email:
        values["SUPPORT_EMAIL"] = email
    values["PUBLISH_BACKEND"] = publish
    values["HITL_AUTO_APPROVE"] = "false"
    values["HITL_MODE"] = values.get("HITL_MODE") or "external_only"
    values["CONTENTFORGE_API_KEY"] = _gen_key("cf_admin_")
    values["CONTENTFORGE_WIDGET_KEY"] = _gen_key("pk_live_")
    if xai:
        values["XAI_API_KEY"] = xai
    else:
        values["XAI_API_KEY"] = values.get("XAI_API_KEY") or ""
    if publish == "wordpress":
        values["WORDPRESS_SITE_URL"] = wp_url
        values["WORDPRESS_USERNAME"] = wp_user
        values["WORDPRESS_APP_PASSWORD"] = wp_pass
    # stash non-env for brand writer
    values["_website"] = website
    values["_voice"] = voice
    values["_business"] = business
    return values


# ─── smoke / serve ───────────────────────────────────────────────────────────

def _run_smoke(py: Path) -> None:
    _info("Running a quick self-check…")
    env = os.environ.copy()
    # ensure we load the new .env via dotenv in config
    r = subprocess.run(
        [str(py), "scripts/smoke_test.py"],
        cwd=str(ROOT),
        env=env,
    )
    if r.returncode != 0:
        _err("Self-check failed. You can re-run:  python scripts/bootstrap.py")
        raise SystemExit(1)
    _ok("Self-check passed — Content desk is ready")


def _wait_health(timeout: float = 45.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urlopen(HEALTH_URL, timeout=2) as resp:  # noqa: S310 — local only
                if resp.status == 200:
                    return True
        except (URLError, OSError, TimeoutError):
            time.sleep(0.6)
    return False


def _start_server(py: Path, *, open_browser: bool) -> subprocess.Popen:
    _info(f"Starting Content desk on port {DEFAULT_PORT}…")
    # Detached-ish: keep attached so Ctrl+C stops it, but open browser when healthy
    proc = subprocess.Popen(
        [str(py), "-m", "src.cli", "serve", "--port", str(DEFAULT_PORT)],
        cwd=str(ROOT),
    )
    if _wait_health():
        _ok("Content desk is running")
        print()
        print(f"  Workspace:  {WORKSPACE_URL}")
        print(f"  Health:     {HEALTH_URL}")
        print()
        print("  Safety: nothing publishes until you approve it.")
        print("  Press Ctrl+C in this window to stop the desk.")
        print()
        if open_browser:
            try:
                webbrowser.open(WORKSPACE_URL)
                _ok("Opened your content workspace in the browser")
            except Exception:  # noqa: BLE001
                _warn("Open this address in your browser:")
                print(f"     {WORKSPACE_URL}")
    else:
        _warn("Server started but health check timed out — try opening the workspace URL manually.")
        print(f"     {WORKSPACE_URL}")
    return proc


# ─── main ────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Set up Matrixly Content desk — only asks for business details and optional secrets.",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Use safe defaults (local publish, generic brand); minimal prompts",
    )
    parser.add_argument(
        "--no-serve",
        action="store_true",
        help="Install and configure only; do not start the server",
    )
    parser.add_argument(
        "--skip-smoke",
        action="store_true",
        help="Skip the self-check (not recommended)",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not open the workspace in a browser",
    )
    parser.add_argument(
        "--reconfigure",
        action="store_true",
        help="Ask questions again even if .env already exists",
    )
    args = parser.parse_args(argv)

    os.chdir(ROOT)
    _banner()

    try:
        _ensure_python()
        py = _ensure_venv()
        _pip_install(py)

        print()
        if ENV_PATH.is_file() and not args.reconfigure and not args.yes:
            _ok(f"Found existing {ENV_PATH.name}")
            if _prompt_yes_no("Keep current settings?", default=True):
                answers = None
            else:
                answers = _collect_answers(assume_yes=False)
        elif ENV_PATH.is_file() and args.yes and not args.reconfigure:
            _ok(f"Keeping existing {ENV_PATH.name}")
            answers = None
        else:
            answers = _collect_answers(assume_yes=args.yes)

        if answers is not None:
            website = answers.pop("_website", "")
            voice = answers.pop("_voice", "")
            business = answers.pop("_business", answers.get("BUSINESS_NAME", "My Business"))
            _write_env(answers)
            _write_brand_voice(
                business_name=business,
                website=website,
                voice_notes=voice,
            )
        elif not VOICE_PATH.is_file():
            _write_brand_voice(business_name="My Business", website="", voice_notes="")

        print()
        if not args.skip_smoke:
            _run_smoke(py)
        else:
            _warn("Skipped self-check")

        print()
        print("─" * 60)
        print("  You're set up")
        print("─" * 60)
        print()
        print(f"  {PRIVACY}")
        print()
        print("  Next time you can start with:")
        if sys.platform == "win32":
            print("    .\\.venv\\Scripts\\python.exe -m src.cli serve")
            print("  Or double-click:  scripts\\Start Content Desk.cmd")
        else:
            print("    .venv/bin/python -m src.cli serve")
        print()

        if args.no_serve:
            _info("Install complete (--no-serve). Start when ready with the command above.")
            return 0

        if args.yes:
            start = True
        else:
            start = _prompt_yes_no("Start Content desk and open the workspace now?", default=True)

        if not start:
            _info("OK — start later with the command above.")
            return 0

        proc = _start_server(py, open_browser=not args.no_browser)
        try:
            return proc.wait()
        except KeyboardInterrupt:
            print()
            _info("Stopping Content desk…")
            proc.terminate()
            try:
                proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                proc.kill()
            _ok("Stopped")
            return 0

    except subprocess.CalledProcessError as exc:
        _err(f"A setup step failed (exit {exc.returncode}).")
        _info("You can send this screen to Matrixly support — do not paste any passwords.")
        return 1
    except KeyboardInterrupt:
        print()
        _warn("Setup cancelled.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
