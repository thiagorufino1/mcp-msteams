from __future__ import annotations

from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from mcp_msteams.graph.cache import cached_get
from mcp_msteams.graph.errors import (
    AuthError,
    GraphError,
    GraphValidationError,
    NotFoundError,
    ServiceUnavailableError,
    ThrottlingError,
)
from mcp_msteams.security.auth import get_token

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"

_http_client = httpx.AsyncClient(
    base_url=GRAPH_BASE_URL,
    timeout=httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=5.0),
    limits=httpx.Limits(max_connections=100, max_keepalive_connections=50),
)

_GRAPH_RETRY = retry(
    retry=retry_if_exception_type((ThrottlingError, ServiceUnavailableError)),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(4),
    reraise=True,
)


def _raise_for_status(response: httpx.Response, path: str) -> None:
    code = response.status_code
    if code == 429:
        wait = int(response.headers.get("Retry-After", "5"))
        raise ThrottlingError(f"Rate limited on {path}, retry after {wait}s", code)
    if code == 404:
        raise NotFoundError(f"Not found: {path}", code)
    if code in (401, 403):
        raise AuthError(f"Auth error {code} on {path}", code)
    if code == 400:
        raise GraphValidationError(f"Bad request on {path}: {response.text[:200]}", code)
    if code >= 500:
        raise ServiceUnavailableError(f"Server error {code} on {path}", code)
    if response.is_error:
        raise GraphError(f"Graph error {code} on {path}", code)


async def _do_request(
    method: str,
    path: str,
    token: str,
    params: dict[str, Any] | None,
    extra_headers: dict[str, str] | None = None,
) -> Any:
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    if extra_headers:
        headers.update(extra_headers)
    response = await _http_client.request(method, path, headers=headers, params=params)
    _raise_for_status(response, path)
    if not response.content:
        return {}
    content_type = response.headers.get("content-type", "")
    if "json" in content_type:
        return response.json()
    # $count endpoints return plain text integers — return as string for callers to cast
    try:
        return response.json()
    except Exception:
        return response.text


async def graph_get(
    path: str,
    scopes: list[str],
    params: dict[str, Any] | None = None,
    cache_key: str | None = None,
    ttl: float = 0,
    extra_headers: dict[str, str] | None = None,
) -> Any:
    token = get_token(scopes)

    @_GRAPH_RETRY
    async def _retried() -> Any:
        return await _do_request("GET", path, token, params, extra_headers)

    if cache_key and ttl > 0:
        return await cached_get(cache_key, ttl, _retried)
    return await _retried()


async def graph_get_all(
    path: str,
    scopes: list[str],
    params: dict[str, Any] | None = None,
    max_pages: int = 10,
    extra_headers: dict[str, str] | None = None,
) -> list[Any]:
    """Fetch all pages from a paginated Graph endpoint via @odata.nextLink."""
    token = get_token(scopes)
    results: list[Any] = []
    next_url: str | None = path
    current_params: dict[str, Any] | None = params
    pages = 0

    @_GRAPH_RETRY
    async def _fetch_page(url: str, p: dict[str, Any] | None) -> Any:
        return await _do_request("GET", url, token, p, extra_headers)

    while next_url and pages < max_pages:
        data = await _fetch_page(next_url, current_params)
        results.extend(data.get("value", []))
        next_url = data.get("@odata.nextLink")
        current_params = None  # nextLink already contains query params
        pages += 1

    return results


async def graph_get_paged(
    path: str,
    scopes: list[str],
    params: dict[str, Any] | None = None,
    max_pages: int = 50,
    extra_headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Paginate a Graph endpoint collecting all items while preserving @odata.count.

    Unlike graph_get_all (which returns a flat list), this preserves the total
    count from the first response and reports whether more pages exist.

    Returns:
        {
            "items": list of all collected items,
            "total": @odata.count from the first page (or None),
            "pages_fetched": number of pages retrieved,
            "has_more": True if stopped before exhausting all pages,
        }
    """
    token = get_token(scopes)
    items: list[Any] = []
    next_url: str | None = path
    current_params: dict[str, Any] | None = params
    total: int | None = None
    pages = 0

    @_GRAPH_RETRY
    async def _fetch(url: str, p: dict[str, Any] | None) -> Any:
        return await _do_request("GET", url, token, p, extra_headers)

    while next_url and pages < max_pages:
        data = await _fetch(next_url, current_params)
        if total is None and "@odata.count" in data:
            total = int(data["@odata.count"])
        items.extend(data.get("value", []))
        next_url = data.get("@odata.nextLink")
        current_params = None
        pages += 1

    return {
        "items": items,
        "total": total,
        "pages_fetched": pages,
        "has_more": next_url is not None,
    }
