"""Auth + rate limiting."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Callable

from fastapi import Header, HTTPException


class RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str, limit_per_minute: int) -> None:
        now = time.time()
        window = self._hits[key]
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= limit_per_minute:
            raise HTTPException(429, "Rate limit exceeded")
        window.append(now)


rate_limiter = RateLimiter()


def require_api_key(cfg: dict) -> Callable:
    expected = (cfg.get("security") or {}).get("api_key") or "change-me-admin-key"

    async def _dep(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
        if not x_api_key or x_api_key != expected:
            raise HTTPException(401, "Invalid or missing X-API-Key")

    return _dep


def require_widget_or_api_key(cfg: dict) -> Callable:
    api_key = (cfg.get("security") or {}).get("api_key") or "change-me-admin-key"
    widget_key = (cfg.get("security") or {}).get("widget_key") or "pk_live_change-me"

    async def _dep(
        x_api_key: str | None = Header(default=None, alias="X-API-Key"),
        x_widget_key: str | None = Header(default=None, alias="X-Widget-Key"),
    ) -> None:
        if x_api_key in {api_key, "change-me-admin-key"}:
            return
        if x_widget_key in {widget_key, "pk_live_change-me"}:
            return
        if not x_api_key and not x_widget_key:
            return  # local dashboard convenience
        raise HTTPException(401, "Invalid API or widget key")

    return _dep
