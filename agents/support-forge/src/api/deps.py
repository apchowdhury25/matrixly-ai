"""Auth + rate limiting dependencies."""

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


def require_widget_or_api_key(cfg: dict) -> Callable:
    api = (cfg.get("security") or {}).get("api_key") or ""
    widget = (cfg.get("security") or {}).get("widget_key") or ""

    async def _dep(
        request: Request,
        x_api_key: str | None = Header(default=None),
        x_widget_key: str | None = Header(default=None),
    ) -> None:
        key = x_widget_key or x_api_key or ""
        if key and key in {api, widget}:
            # Origin allowlist when browser sends Origin
            origin = request.headers.get("origin")
            allowed = cfg.get("cors_origins") or []
            if origin and allowed and origin not in allowed and origin != "null":
                # Allow missing strictness for local file:// testing via null sometimes
                if origin not in allowed:
                    raise HTTPException(status_code=403, detail="Origin not allowed")
            return
        raise HTTPException(status_code=401, detail="Invalid or missing widget/API key")

    return _dep
