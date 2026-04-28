"""TTL cache with stampede prevention for Graph API responses."""

from __future__ import annotations

import asyncio
import time
from typing import Any, Awaitable, Callable

_store: dict[str, tuple[Any, float]] = {}
_locks: dict[str, asyncio.Lock] = {}


async def cached_get(
    key: str,
    ttl: float,
    fetcher: Callable[[], Awaitable[Any]],
) -> Any:
    """
    Fetch a value with TTL caching and cache stampede prevention.

    Args:
        key: Cache key
        ttl: Time-to-live in seconds
        fetcher: Async callable that fetches the value if not cached

    Returns:
        Cached value or result from fetcher
    """
    now = time.monotonic()
    entry = _store.get(key)
    if entry and now - entry[1] < ttl:
        return entry[0]

    if key not in _locks:
        _locks[key] = asyncio.Lock()

    async with _locks[key]:
        entry = _store.get(key)
        if entry and time.monotonic() - entry[1] < ttl:
            return entry[0]
        result = await fetcher()
        _store[key] = (result, time.monotonic())
        return result


def clear_cache() -> None:
    """Clear all cached entries and locks."""
    _store.clear()
    _locks.clear()
