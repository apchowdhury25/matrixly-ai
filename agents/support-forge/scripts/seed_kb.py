#!/usr/bin/env python3
"""Re-index knowledge/ into the local vector store."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import load_config
from src.orchestrator import SupportForge


def main() -> int:
    cfg = load_config()
    forge = SupportForge(cfg)
    result = forge.seed_knowledge()
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
