#!/usr/bin/env python3
"""Mint a development JWT with tenant_id claim (English claim names)."""

from __future__ import annotations

import argparse
import os
import time
from uuid import uuid4

from jose import jwt


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--tenant-id", default=str(uuid4()))
    p.add_argument("--sub", default="dev-user@matrixly.net")
    p.add_argument("--secret", default=os.getenv("JWT_SECRET", "change-me-to-a-long-random-string"))
    p.add_argument("--audience", default=os.getenv("JWT_AUDIENCE", "matrixly-api"))
    p.add_argument("--hours", type=int, default=24)
    args = p.parse_args()

    now = int(time.time())
    claims = {
        "sub": args.sub,
        "tenant_id": args.tenant_id,
        "roles": ["owner"],
        "iat": now,
        "exp": now + args.hours * 3600,
        "aud": args.audience,
    }
    token = jwt.encode(claims, args.secret, algorithm="HS256")
    print(token)
    print(f"# tenant_id={args.tenant_id}", flush=True)


if __name__ == "__main__":
    main()
