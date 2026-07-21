"""Load agent configuration and environment."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
SUMMARIES_DIR = DATA_DIR / "summaries"

# Named mailbox profiles (override via EMAIL_PROFILE)
PROFILES: dict[str, dict[str, Any]] = {
    "hostinger": {
        "primary_email": "anwar.chowdhury@matrixbazaar.com",
        "imap_host": "imap.hostinger.com",
        "imap_port": 993,
        "smtp_host": "smtp.hostinger.com",
        "smtp_port": 465,
        "drafts_folder": "INBOX.Drafts",
        "sent_folder": "INBOX.Sent",
        "user_env": "EMAIL_HOSTINGER_USER",
        "pass_env": "EMAIL_HOSTINGER_PASSWORD",
        # fallback env keys
        "user_env_alt": "EMAIL_IMAP_USER",
        "pass_env_alt": "EMAIL_IMAP_PASSWORD",
    },
    "gmail": {
        "primary_email": "usmatrixbazaar@gmail.com",
        "imap_host": "imap.gmail.com",
        "imap_port": 993,
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 465,
        "drafts_folder": "[Gmail]/Drafts",
        "sent_folder": "[Gmail]/Sent Mail",
        "user_env": "EMAIL_GMAIL_USER",
        "pass_env": "EMAIL_GMAIL_PASSWORD",
        "user_env_alt": "EMAIL_IMAP_USER",
        "pass_env_alt": "EMAIL_IMAP_PASSWORD",
    },
}


def load_config(path: Path | None = None) -> dict[str, Any]:
    load_dotenv(ROOT / ".env", override=True)
    cfg_path = path or (ROOT / "config.yaml")
    with open(cfg_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    profile_name = (
        os.getenv("EMAIL_PROFILE")
        or (cfg.get("agent") or {}).get("profile")
        or "gmail"
    ).lower().strip()
    if profile_name not in PROFILES:
        # allow alias
        if profile_name in {"google", "gmail-imap"}:
            profile_name = "gmail"
        elif profile_name in {"matrixbazaar", "hostinger-imap", "thunderbird"}:
            profile_name = "hostinger"
        else:
            profile_name = "gmail"

    profile = PROFILES[profile_name]
    cfg.setdefault("agent", {})["profile"] = profile_name
    cfg["agent"]["backend"] = (
        os.getenv("EMAIL_BACKEND")
        or cfg["agent"].get("backend")
        or "imap"
    ).lower()

    # If user forces gmail API backend
    if cfg["agent"]["backend"] in {"gmail_api", "google_api"}:
        cfg["agent"]["backend"] = "gmail"

    account = cfg.setdefault("account", {})
    user = (
        os.getenv(profile["user_env"])
        or os.getenv(profile["user_env_alt"])
        or os.getenv("EMAIL_ASSISTANT_PRIMARY")
        or profile["primary_email"]
    )
    password = os.getenv(profile["pass_env"]) or os.getenv(profile["pass_env_alt"]) or ""

    account["primary_email"] = user
    account.setdefault("domains", [])
    for d in ("gmail.com", "matrixbazaar.com", "usmatrixbazaar.com", "matrixly.ai"):
        if d not in account["domains"]:
            account["domains"].append(d)

    # Gmail API OAuth files (optional path)
    gmail = cfg.setdefault("gmail", {})
    for key, envk, default in (
        ("credentials_file", "GMAIL_CREDENTIALS_FILE", "data/credentials.json"),
        ("token_file", "GMAIL_TOKEN_FILE", "data/token.json"),
    ):
        p = Path(os.getenv(envk) or gmail.get(key) or default)
        if not p.is_absolute():
            p = ROOT / p
        gmail[key] = str(p)

    # IMAP / SMTP for active profile
    imap = cfg.setdefault("imap", {})
    smtp = cfg.setdefault("smtp", {})

    # Explicit env hosts always win
    imap["host"] = os.getenv("EMAIL_IMAP_HOST") or profile["imap_host"]
    imap["port"] = int(os.getenv("EMAIL_IMAP_PORT") or profile["imap_port"])
    imap["username"] = user
    if password:
        imap["password"] = password
    imap["inbox"] = os.getenv("EMAIL_IMAP_INBOX") or imap.get("inbox") or "INBOX"
    imap["drafts_folder"] = (
        os.getenv("EMAIL_IMAP_DRAFTS")
        or profile["drafts_folder"]
    )
    imap["sent_folder"] = (
        os.getenv("EMAIL_IMAP_SENT")
        or profile["sent_folder"]
    )
    imap.setdefault("max_results", 40)

    smtp["host"] = os.getenv("EMAIL_SMTP_HOST") or profile["smtp_host"]
    smtp["port"] = int(os.getenv("EMAIL_SMTP_PORT") or profile["smtp_port"])

    # Summary deliver_to follows active mailbox unless overridden
    summary = cfg.setdefault("summary", {})
    if not os.getenv("EMAIL_SUMMARY_TO"):
        summary["deliver_to"] = user
    else:
        summary["deliver_to"] = os.getenv("EMAIL_SUMMARY_TO")

    # Draft signature from address should match active mailbox
    draft = cfg.setdefault("draft", {})
    if profile_name == "gmail" and "gmail.com" in user:
        draft.setdefault(
            "signature",
            (
                "—\n"
                "Anwar Pasha Chowdhury\n"
                "CEO, Matrix Bazaar LLC / Matrixly.AI\n"
                "Houston, TX\n"
                f"{user}"
            ),
        )

    xai = cfg.setdefault("xai", {})
    if os.getenv("XAI_API_KEY"):
        xai["api_key"] = os.getenv("XAI_API_KEY")
    xai["enabled"] = bool(xai.get("enabled", True)) and bool(
        xai.get("api_key") or os.getenv("XAI_API_KEY")
    )

    cfg["_profile_meta"] = {
        "name": profile_name,
        "pass_env": profile["pass_env"],
        "user_env": profile["user_env"],
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)
    return cfg
