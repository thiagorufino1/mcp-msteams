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
    timeout=30.0,
    limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
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
    return response.json() if response.content else {}


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
