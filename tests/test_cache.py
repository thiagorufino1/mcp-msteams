"""Tests for TTL cache implementation."""

import asyncio

import pytest

from app.graph.cache import cached_get, clear_cache


@pytest.mark.asyncio
async def test_cache_hit_returns_same_value():
    """Test that cached values are returned without re-fetching."""
    call_count = 0

    async def fetcher():
        nonlocal call_count
        call_count += 1
        return {"data": "value"}

    clear_cache()
    result1 = await cached_get("key1", ttl=60, fetcher=fetcher)
    result2 = await cached_get("key1", ttl=60, fetcher=fetcher)

    assert result1 == {"data": "value"}
    assert result2 == {"data": "value"}
    assert call_count == 1


@pytest.mark.asyncio
async def test_cache_miss_after_ttl():
    """Test that cache expires after TTL."""
    call_count = 0

    async def fetcher():
        nonlocal call_count
        call_count += 1
        return {"count": call_count}

    clear_cache()
    r1 = await cached_get("key2", ttl=0.01, fetcher=fetcher)
    await asyncio.sleep(0.05)
    r2 = await cached_get("key2", ttl=0.01, fetcher=fetcher)

    assert r1 == {"count": 1}
    assert r2 == {"count": 2}
    assert call_count == 2


@pytest.mark.asyncio
async def test_cache_stampede_prevention():
    """Test that cache stampede is prevented (fetcher only called once for concurrent requests)."""
    call_count = 0

    async def slow_fetcher():
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.05)
        return {"data": "slow"}

    clear_cache()
    results = await asyncio.gather(
        cached_get("key3", ttl=60, fetcher=slow_fetcher),
        cached_get("key3", ttl=60, fetcher=slow_fetcher),
        cached_get("key3", ttl=60, fetcher=slow_fetcher),
    )
    assert all(r == {"data": "slow"} for r in results)
    assert call_count == 1
