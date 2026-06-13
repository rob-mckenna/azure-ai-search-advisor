"""In-memory response caching for repeated API requests."""

from __future__ import annotations

import hashlib
import json
import os
from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass
from threading import Lock
from time import monotonic
from typing import Any


def _env_flag(name: str, default: str) -> bool:
    return os.environ.get(name, default).strip().lower() == "true"


def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name, str(default)).strip()
    try:
        return int(value)
    except ValueError:
        return default


@dataclass(slots=True)
class _CacheEntry:
    value: Any
    expires_at: float


class ResponseCache:
    """Thread-safe TTL cache with LRU eviction."""

    def __init__(
        self,
        *,
        enabled: bool = False,
        ttl_seconds: int = 300,
        max_entries: int = 100,
    ) -> None:
        self._enabled = enabled
        self._ttl_seconds = max(ttl_seconds, 1)
        self._max_entries = max(max_entries, 1)
        self._entries: OrderedDict[str, _CacheEntry] = OrderedDict()
        self._lock = Lock()

    @classmethod
    def from_env(cls) -> "ResponseCache":
        return cls(
            enabled=_env_flag("CACHE_ENABLED", "false"),
            ttl_seconds=_env_int("CACHE_TTL_SECONDS", 300),
            max_entries=_env_int("CACHE_MAX_ENTRIES", 100),
        )

    def build_key(self, payload: Any) -> str:
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def get(self, key: str) -> Any | None:
        if not self._enabled:
            return None

        now = monotonic()
        with self._lock:
            self._evict_expired(now)
            entry = self._entries.get(key)
            if entry is None:
                return None
            self._entries.move_to_end(key)
            return deepcopy(entry.value)

    def set(self, key: str, value: Any) -> None:
        if not self._enabled:
            return

        now = monotonic()
        with self._lock:
            self._evict_expired(now)
            self._entries[key] = _CacheEntry(
                value=deepcopy(value),
                expires_at=now + self._ttl_seconds,
            )
            self._entries.move_to_end(key)
            while len(self._entries) > self._max_entries:
                self._entries.popitem(last=False)

    def _evict_expired(self, now: float) -> None:
        expired_keys = [key for key, entry in self._entries.items() if entry.expires_at <= now]
        for key in expired_keys:
            self._entries.pop(key, None)
