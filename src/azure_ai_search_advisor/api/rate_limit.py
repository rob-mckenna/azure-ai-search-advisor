"""Rate limiting helpers for FastAPI routes."""

from __future__ import annotations

import os
from collections import defaultdict, deque
from math import ceil
from threading import Lock
from time import monotonic

from fastapi import HTTPException, Request, status


class SlidingWindowRateLimiter:
    """Track requests per client within a moving time window."""

    def __init__(self) -> None:
        self._requests: defaultdict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, client_ip: str, *, limit: int, window_seconds: int) -> int | None:
        """Return retry-after seconds when the client exceeds the limit."""

        now = monotonic()
        window_start = now - window_seconds

        with self._lock:
            request_times = self._requests[client_ip]
            while request_times and request_times[0] <= window_start:
                request_times.popleft()

            if len(request_times) >= limit:
                retry_after = max(1, ceil(window_seconds - (now - request_times[0])))
                return retry_after

            request_times.append(now)
            return None


_rate_limiter = SlidingWindowRateLimiter()


def _env_flag(name: str, default: str) -> bool:
    return os.environ.get(name, default).strip().lower() == "true"


def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name, str(default)).strip()
    try:
        return int(value)
    except ValueError:
        return default


def _extract_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


async def check_rate_limit(request: Request) -> None:
    """Enforce a simple sliding-window rate limit for protected routes."""

    if not _env_flag("RATE_LIMIT_ENABLED", "false"):
        return

    limit = _env_int("RATE_LIMIT_REQUESTS", 60)
    window_seconds = _env_int("RATE_LIMIT_WINDOW_SECONDS", 60)
    if limit <= 0 or window_seconds <= 0:
        return

    retry_after = _rate_limiter.check(
        _extract_client_ip(request),
        limit=limit,
        window_seconds=window_seconds,
    )
    if retry_after is None:
        return

    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Rate limit exceeded. Try again later.",
        headers={"Retry-After": str(retry_after)},
    )
