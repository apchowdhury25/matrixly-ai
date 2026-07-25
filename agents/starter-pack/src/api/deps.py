"""Auth + rate limiting."""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Callable

from fastapi import Header, HTTPException, Request


class RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str, limit: int, window_sec: int = 60) -> None:
        now = time.time()
        bucket = self._hits[key]
        self._hits[key] = [t for t in bucket if now - t < window_sec]
        if len(self._hits[key]) >= limit:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        self._hits[key].append(now)


rate_limiter = RateLimiter()


def require_api_key(cfg: dict) -> Callable:
    expected = (cfg.get("security") or {}).get("api_key") or ""

    async def _dep(x_api_key: str | None = Header(default=None)) -> None:
        if not expected or x_api_key != expected:
            raise HTTPException(status_code=401, detail="Invalid or missing API key")

    return _dep
