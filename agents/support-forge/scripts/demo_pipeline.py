#!/usr/bin/env python3
"""Run sample SupportForge questions end-to-end."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["demo"]))
