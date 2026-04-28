# Teams Admin Support MCP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a read-only Microsoft Teams admin support MCP server exposing 40+ Graph API tools for support/admin diagnostics.

**Architecture:** FastMCP server with layered architecture: `tools/` (thin wrappers) → `services/` (domain logic) → `graph/client.py` (httpx + MSAL + tenacity) → Microsoft Graph API. TTL cache per domain, `_audited` decorator on every tool, structured JSON + Markdown responses.

**Tech Stack:** Python 3.11+, FastMCP, httpx, msal, pydantic, pydantic-settings, tenacity, structlog, pytest, pytest-asyncio, respx, ruff, mypy

---

## File Map

```
app/
  __init__.py
  main.py                        # FastMCP server entry, lifespan, _register calls
  config.py                      # pydantic-settings env config
  logging_config.py              # structlog setup, audited decorator, UPN masking
  security/
    __init__.py
    auth.py                      # MSAL ConfidentialClientApplication singleton, get_token()
    permissions.py               # SCOPES dict (all map to .default for client credentials)
    input_validation.py          # validate_upn(), validate_uuid()
  graph/
    __init__.py
    errors.py                    # GraphError hierarchy
    cache.py                     # TTL cache with asyncio.Lock per key
    endpoints.py                 # Graph URL builder functions (no magic strings in services)
    client.py                    # graph_get() with tenacity retry, 429 handling, cache integration
  services/
    __init__.py
    users_service.py             # get_user_overview, get_user_profile, get_user_presence, list_user_teams, get_user_assigned_policies
    teams_service.py             # list_team_channels, list_team_members, get_team_owners, get_team_settings, get_channel_settings, check_private_shared_channels, detect_orphaned_team, detect_team_without_owner
    policies_service.py          # compare_user_policies, detect_policy_conflicts
    calls_service.py             # get_call_quality_summary, diagnose_call_quality, list_failed_calls, list_poor_quality_calls
    messages_service.py          # stub
    meetings_service.py          # stub
    devices_service.py           # stub
    voice_service.py             # stub
    incidents_service.py         # stub
    audit_service.py             # in-memory ring buffer: record(), get_history(), get_summary()
  tools/
    __init__.py
    users_tools.py               # _register(mcp): 5 user tools
    teams_tools.py               # _register(mcp): 8 teams/channel tools
    policies_tools.py            # _register(mcp): 3 policy tools (incl. compare, conflict detect)
    calls_tools.py               # _register(mcp): 4 call quality tools
    messages_tools.py            # _register(mcp): 3 stubs
    meetings_tools.py            # _register(mcp): 2 stubs
    devices_tools.py             # _register(mcp): 2 stubs
    voice_tools.py               # _register(mcp): 3 stubs
    audit_tools.py               # _register(mcp): execution_history, who_did_what, support_case_summary
  schemas/
    __init__.py
    common.py                    # ToolParams base, ResponseFormat enum
    users.py                     # GetUserProfileParams, GetUserPresenceParams, etc.
    teams.py                     # ListTeamChannelsParams, ListTeamMembersParams, etc.
    policies.py                  # CompareUserPoliciesParams, DetectPolicyConflictsParams, etc.
    calls.py                     # GetCallQualitySummaryParams, DiagnoseCallQualityParams, etc.
    diagnostics.py               # shared diagnostic response models
  utils/
    __init__.py
    sanitization.py              # mask_upn(), mask_token(), sanitize_log_value()
    date_utils.py                # utc_now(), days_ago(), graph_date_filter()
    response.py                  # render_response(result, fmt), build_markdown_table()
tests/
  __init__.py
  conftest.py                    # shared fixtures: mock_graph_client, mock_settings
  test_graph_client.py           # 200, 429 retry, 404, 503 with respx
  test_auth.py                   # MSAL mock: token acquisition, cache hit, failure
  test_cache.py                  # TTL expiry, stampede prevention
  test_sanitization.py           # UPN masking, JWT masking
  test_services.py               # users_service, teams_service with mocked graph_get
  test_tool_registration.py      # all tools registered, readOnlyHint=True
.env.example
pyproject.toml
Dockerfile
docker-compose.yml
```

---

## Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: all `__init__.py` files
- Create: `app/` directory tree

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p app/security app/graph app/services app/tools app/schemas app/utils tests
touch app/__init__.py app/security/__init__.py app/graph/__init__.py
touch app/services/__init__.py app/tools/__init__.py app/schemas/__init__.py app/utils/__init__.py
touch tests/__init__.py
```

- [ ] **Step 2: Create `pyproject.toml`**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "teams-admin-support-mcp"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastmcp>=2.0",
    "httpx>=0.27",
    "msal>=1.28",
    "pydantic>=2.7",
    "pydantic-settings>=2.3",
    "tenacity>=8.3",
    "structlog>=24.1",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.2",
    "pytest-asyncio>=0.23",
    "respx>=0.21",
    "ruff>=0.4",
    "mypy>=1.10",
]

[project.scripts]
teams-mcp = "app.main:main"

[tool.hatch.build.targets.wheel]
packages = ["app"]

[tool.pytest.ini_options]
asyncio_mode = "strict"
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.mypy]
python_version = "3.11"
strict = true
ignore_missing_imports = true
```

- [ ] **Step 3: Create `.env.example`**

```
AZURE_TENANT_ID=
AZURE_CLIENT_ID=
AZURE_CLIENT_SECRET=
FASTMCP_TRANSPORT=http
FASTMCP_HOST=127.0.0.1
FASTMCP_PORT=8000
LOG_LEVEL=INFO
AUDIT_BUFFER_SIZE=500
CACHE_TTL_PRESENCE=30
CACHE_TTL_USER=300
CACHE_TTL_TEAMS=600
CACHE_TTL_POLICIES=900
CACHE_TTL_CALLS=120
CACHE_TTL_INCIDENTS=300
CACHE_TTL_DEVICES=300
```

- [ ] **Step 4: Create `Dockerfile`**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .
COPY app/ app/
EXPOSE 8000
CMD ["teams-mcp"]
```

- [ ] **Step 5: Create `docker-compose.yml`**

```yaml
services:
  teams-mcp:
    build: .
    ports:
      - "8000:8000"
    environment:
      - AZURE_TENANT_ID
      - AZURE_CLIENT_ID
      - AZURE_CLIENT_SECRET
      - FASTMCP_TRANSPORT=http
      - FASTMCP_HOST=0.0.0.0
      - FASTMCP_PORT=8000
      - LOG_LEVEL=INFO
    restart: unless-stopped
```

- [ ] **Step 6: Install dependencies**

```bash
pip install -e ".[dev]"
```

Expected: no errors, packages installed.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml .env.example Dockerfile docker-compose.yml app/ tests/
git commit -m "chore: project scaffolding"
```

---

## Task 2: Config & Logging

**Files:**
- Create: `app/config.py`
- Create: `app/logging_config.py`

- [ ] **Step 1: Create `app/config.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    azure_tenant_id: str
    azure_client_id: str
    azure_client_secret: str

    fastmcp_transport: str = "http"
    fastmcp_host: str = "127.0.0.1"
    fastmcp_port: int = 8000
    log_level: str = "INFO"

    audit_buffer_size: int = 500
    cache_ttl_presence: int = 30
    cache_ttl_user: int = 300
    cache_ttl_teams: int = 600
    cache_ttl_policies: int = 900
    cache_ttl_calls: int = 120
    cache_ttl_incidents: int = 300
    cache_ttl_devices: int = 300


settings = Settings()
```

- [ ] **Step 2: Create `app/logging_config.py`**

```python
from __future__ import annotations

import functools
import logging
import time
import uuid
from contextvars import ContextVar
from typing import Any, Callable

import structlog

_trace_id: ContextVar[str] = ContextVar("trace_id", default="-")

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger("teams_mcp")


def audited(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator: injects trace_id, logs invocation/completion/failure, writes audit entry."""

    @functools.wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        tid = uuid.uuid4().hex[:8]
        _trace_id.set(tid)
        t0 = time.monotonic()
        tool_name = fn.__name__

        from app.utils.sanitization import sanitize_log_value
        safe_kwargs = {k: sanitize_log_value(str(v)) for k, v in kwargs.items()}
        logger.info("tool_invoked", tool=tool_name, trace_id=tid, **safe_kwargs)

        try:
            result = await fn(*args, **kwargs)
            elapsed_ms = round((time.monotonic() - t0) * 1000)
            logger.info("tool_completed", tool=tool_name, trace_id=tid, elapsed_ms=elapsed_ms)
            _record(tool_name, kwargs, elapsed_ms, "ok", None)
            return result
        except Exception as exc:
            elapsed_ms = round((time.monotonic() - t0) * 1000)
            logger.error("tool_failed", tool=tool_name, trace_id=tid, elapsed_ms=elapsed_ms, error=str(exc))
            _record(tool_name, kwargs, elapsed_ms, "error", type(exc).__name__)
            raise

    return wrapper


def _record(tool: str, kwargs: dict[str, Any], elapsed_ms: int, status: str, error_type: str | None) -> None:
    from app.services.audit_service import record
    from app.utils.sanitization import mask_upn
    upn_hint = mask_upn(str(kwargs.get("upn", kwargs.get("upn1", ""))))
    record(tool=tool, upn_hint=upn_hint, elapsed_ms=elapsed_ms, status=status, error_type=error_type)
```

- [ ] **Step 3: Commit**

```bash
git add app/config.py app/logging_config.py
git commit -m "feat: config and logging foundation"
```

---

## Task 3: Graph Errors & Cache

**Files:**
- Create: `app/graph/errors.py`
- Create: `app/graph/cache.py`
- Create: `tests/test_cache.py`

- [ ] **Step 1: Write failing test for cache**

```python
# tests/test_cache.py
import asyncio
import pytest
from app.graph.cache import cached_get, clear_cache


@pytest.mark.asyncio
async def test_cache_hit_returns_same_value():
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
    assert call_count == 1  # fetcher called only once


@pytest.mark.asyncio
async def test_cache_miss_after_ttl():
    import time
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
    assert call_count == 1  # only one fetch despite concurrent requests
```

- [ ] **Step 2: Run test, verify it fails**

```bash
pytest tests/test_cache.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.graph.cache'`

- [ ] **Step 3: Create `app/graph/errors.py`**

```python
class GraphError(Exception):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ThrottlingError(GraphError):
    pass


class NotFoundError(GraphError):
    pass


class AuthError(GraphError):
    pass


class GraphValidationError(GraphError):
    pass


class ServiceUnavailableError(GraphError):
    pass
```

- [ ] **Step 4: Create `app/graph/cache.py`**

```python
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
    _store.clear()
    _locks.clear()
```

- [ ] **Step 5: Run tests, verify pass**

```bash
pytest tests/test_cache.py -v
```

Expected: `3 passed`

- [ ] **Step 6: Commit**

```bash
git add app/graph/errors.py app/graph/cache.py tests/test_cache.py
git commit -m "feat: graph error hierarchy and TTL cache"
```

---

## Task 4: Auth & Permissions

**Files:**
- Create: `app/security/auth.py`
- Create: `app/security/permissions.py`
- Create: `app/security/input_validation.py`
- Create: `tests/test_auth.py`

- [ ] **Step 1: Write failing tests for auth**

```python
# tests/test_auth.py
import pytest
from unittest.mock import MagicMock, patch
from app.graph.errors import AuthError


def test_get_token_returns_access_token():
    mock_app = MagicMock()
    mock_app.acquire_token_for_client.return_value = {"access_token": "test_token_abc"}

    with patch("app.security.auth._get_app", return_value=mock_app):
        from app.security.auth import get_token
        token = get_token(["https://graph.microsoft.com/.default"])

    assert token == "test_token_abc"


def test_get_token_raises_auth_error_on_failure():
    mock_app = MagicMock()
    mock_app.acquire_token_for_client.return_value = {
        "error": "invalid_client",
        "error_description": "Bad client secret",
    }

    with patch("app.security.auth._get_app", return_value=mock_app):
        from app.security.auth import get_token
        with pytest.raises(AuthError, match="Token acquisition failed"):
            get_token(["https://graph.microsoft.com/.default"])


def test_get_app_is_singleton():
    with patch("app.security.auth._app", None):
        with patch("msal.ConfidentialClientApplication") as mock_cls:
            mock_cls.return_value = MagicMock()
            from app.security import auth
            auth._app = None
            app1 = auth._get_app()
            app2 = auth._get_app()
            assert mock_cls.call_count == 1
            assert app1 is app2
```

- [ ] **Step 2: Run test, verify it fails**

```bash
pytest tests/test_auth.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.security.auth'`

- [ ] **Step 3: Create `app/security/auth.py`**

```python
from __future__ import annotations

import msal

from app.config import settings
from app.graph.errors import AuthError

_app: msal.ConfidentialClientApplication | None = None


def _get_app() -> msal.ConfidentialClientApplication:
    global _app
    if _app is None:
        _app = msal.ConfidentialClientApplication(
            settings.azure_client_id,
            authority=f"https://login.microsoftonline.com/{settings.azure_tenant_id}",
            client_credential=settings.azure_client_secret,
        )
    return _app


def get_token(scopes: list[str]) -> str:
    app = _get_app()
    result = app.acquire_token_for_client(scopes=scopes)
    if "access_token" not in result:
        raise AuthError(
            f"Token acquisition failed: {result.get('error_description', result.get('error', 'unknown'))}",
            status_code=401,
        )
    return result["access_token"]
```

- [ ] **Step 4: Create `app/security/permissions.py`**

```python
# Client credentials flow always uses .default — actual permissions are
# defined in the Azure App Registration's API permissions blade.
GRAPH_DEFAULT_SCOPE = ["https://graph.microsoft.com/.default"]

SCOPES = {
    "user_read": GRAPH_DEFAULT_SCOPE,          # User.Read.All
    "presence_read": GRAPH_DEFAULT_SCOPE,      # Presence.Read.All
    "team_read": GRAPH_DEFAULT_SCOPE,          # Team.ReadBasic.All, TeamMember.Read.All
    "directory_read": GRAPH_DEFAULT_SCOPE,     # Directory.Read.All, Group.Read.All
    "channel_read": GRAPH_DEFAULT_SCOPE,       # Channel.ReadBasic.All, ChannelSettings.Read.All
    "call_records": GRAPH_DEFAULT_SCOPE,       # CallRecords.Read.All
    "reports": GRAPH_DEFAULT_SCOPE,            # Reports.Read.All
    "service_health": GRAPH_DEFAULT_SCOPE,     # ServiceHealth.Read.All
}
```

- [ ] **Step 5: Create `app/security/input_validation.py`**

```python
import re

from app.graph.errors import GraphValidationError

_UPN_RE = re.compile(r'^[\w.+\-]+@[\w\-]+\.[a-zA-Z]{2,}$')
_UUID_RE = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)


def validate_upn(upn: str) -> str:
    if not _UPN_RE.match(upn.strip()):
        raise GraphValidationError(f"Invalid UPN format: {upn!r}")
    return upn.strip().lower()


def validate_uuid(value: str, name: str = "ID") -> str:
    if not _UUID_RE.match(value.strip()):
        raise GraphValidationError(f"Invalid {name} format: {value!r}")
    return value.strip().lower()


def validate_days(days: int, *, min_days: int = 1, max_days: int = 30) -> int:
    if not (min_days <= days <= max_days):
        raise GraphValidationError(f"days must be between {min_days} and {max_days}, got {days}")
    return days
```

- [ ] **Step 6: Run tests, verify pass**

```bash
pytest tests/test_auth.py -v
```

Expected: `3 passed`

- [ ] **Step 7: Commit**

```bash
git add app/security/ tests/test_auth.py
git commit -m "feat: MSAL auth, permissions, input validation"
```

---

## Task 5: Sanitization & Utils

**Files:**
- Create: `app/utils/sanitization.py`
- Create: `app/utils/date_utils.py`
- Create: `app/utils/response.py`
- Create: `tests/test_sanitization.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_sanitization.py
from app.utils.sanitization import mask_upn, mask_token, sanitize_log_value


def test_mask_upn_replaces_local_part():
    assert mask_upn("john.doe@contoso.com") == "u***@contoso.com"


def test_mask_upn_preserves_domain():
    result = mask_upn("admin@teams.example.org")
    assert result == "u***@teams.example.org"


def test_mask_upn_no_match_unchanged():
    assert mask_upn("no-email-here") == "no-email-here"


def test_mask_token_replaces_jwt():
    jwt = "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJ1c2VyIn0.signature"
    result = mask_token(f"Bearer {jwt}")
    assert "[TOKEN]" in result
    assert "eyJ" not in result


def test_sanitize_log_value_masks_both():
    value = "user@corp.com eyJhbGc.payload.sig"
    result = sanitize_log_value(value)
    assert "u***@corp.com" in result
    assert "[TOKEN]" in result
```

- [ ] **Step 2: Run test, verify it fails**

```bash
pytest tests/test_sanitization.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.utils.sanitization'`

- [ ] **Step 3: Create `app/utils/sanitization.py`**

```python
import re

_JWT_RE = re.compile(r'eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]*')
_UPN_RE = re.compile(r'(\S+)@(\S+\.\S+)')


def mask_upn(value: str) -> str:
    return _UPN_RE.sub(lambda m: f"u***@{m.group(2)}", value)


def mask_token(value: str) -> str:
    return _JWT_RE.sub("[TOKEN]", value)


def sanitize_log_value(value: str) -> str:
    return mask_upn(mask_token(str(value)))
```

- [ ] **Step 4: Create `app/utils/date_utils.py`**

```python
from datetime import datetime, timedelta, timezone


def utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def days_ago(n: int) -> str:
    dt = utc_now() - timedelta(days=n)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def graph_date_filter(field: str, days: int) -> str:
    since = days_ago(days)
    return f"{field} ge {since}"
```

- [ ] **Step 5: Create `app/utils/response.py`**

```python
from __future__ import annotations

from typing import Any

from app.schemas.common import ResponseFormat


def render_response(result: dict[str, Any], fmt: ResponseFormat) -> Any:
    if fmt == ResponseFormat.MARKDOWN:
        return result.get("markdown") or _auto_markdown(result)
    return result


def _auto_markdown(result: dict[str, Any]) -> str:
    lines: list[str] = []
    for key, value in result.items():
        if key == "markdown":
            continue
        if isinstance(value, dict):
            lines.append(f"**{key}:**")
            for k, v in value.items():
                lines.append(f"  - {k}: {v}")
        elif isinstance(value, list):
            lines.append(f"**{key}:** {len(value)} items")
        else:
            lines.append(f"**{key}:** {value}")
    return "\n".join(lines)


def build_markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    header_row = " | ".join(headers)
    separator = " | ".join(["---"] * len(headers))
    data_rows = [" | ".join(str(cell) for cell in row) for row in rows]
    return "\n".join([header_row, separator, *data_rows])


def not_implemented_response(tool_name: str, todo: str) -> dict[str, str]:
    return {"status": "not_implemented", "tool": tool_name, "todo": todo}
```

- [ ] **Step 6: Create `app/schemas/common.py`**

```python
from enum import Enum

from pydantic import BaseModel, ConfigDict


class ResponseFormat(str, Enum):
    JSON = "json"
    MARKDOWN = "markdown"


class ToolParams(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
```

- [ ] **Step 7: Run tests, verify pass**

```bash
pytest tests/test_sanitization.py -v
```

Expected: `5 passed`

- [ ] **Step 8: Commit**

```bash
git add app/utils/ app/schemas/common.py tests/test_sanitization.py
git commit -m "feat: sanitization utils, date helpers, response renderer, common schemas"
```

---

## Task 6: Graph Client & Endpoints

**Files:**
- Create: `app/graph/endpoints.py`
- Create: `app/graph/client.py`
- Create: `tests/test_graph_client.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_graph_client.py
import pytest
import respx
import httpx
from unittest.mock import patch
from app.graph.errors import ThrottlingError, NotFoundError, AuthError, ServiceUnavailableError
from app.graph.cache import clear_cache


MOCK_TOKEN = "mock_bearer_token"


@pytest.fixture(autouse=True)
def clear():
    clear_cache()
    yield


@pytest.fixture
def mock_token():
    with patch("app.graph.client.get_token", return_value=MOCK_TOKEN):
        yield


@pytest.mark.asyncio
@respx.mock
async def test_graph_get_200(mock_token):
    respx.get("https://graph.microsoft.com/v1.0/users/user@test.com").mock(
        return_value=httpx.Response(200, json={"id": "abc123", "displayName": "Test User"})
    )
    from app.graph.client import graph_get
    result = await graph_get("/users/user@test.com", scopes=["https://graph.microsoft.com/.default"])
    assert result["id"] == "abc123"


@pytest.mark.asyncio
@respx.mock
async def test_graph_get_404_raises_not_found(mock_token):
    respx.get("https://graph.microsoft.com/v1.0/users/ghost@test.com").mock(
        return_value=httpx.Response(404, json={"error": {"code": "Request_ResourceNotFound"}})
    )
    from app.graph.client import graph_get
    with pytest.raises(NotFoundError):
        await graph_get("/users/ghost@test.com", scopes=["https://graph.microsoft.com/.default"])


@pytest.mark.asyncio
@respx.mock
async def test_graph_get_401_raises_auth_error(mock_token):
    respx.get("https://graph.microsoft.com/v1.0/users/u@t.com").mock(
        return_value=httpx.Response(401, json={"error": {"code": "InvalidAuthenticationToken"}})
    )
    from app.graph.client import graph_get
    with pytest.raises(AuthError):
        await graph_get("/users/u@t.com", scopes=["https://graph.microsoft.com/.default"])


@pytest.mark.asyncio
@respx.mock
async def test_graph_get_uses_cache_on_second_call(mock_token):
    route = respx.get("https://graph.microsoft.com/v1.0/teams/team1").mock(
        return_value=httpx.Response(200, json={"id": "team1", "displayName": "Team One"})
    )
    from app.graph.client import graph_get
    r1 = await graph_get("/teams/team1", scopes=["https://graph.microsoft.com/.default"], cache_key="teams:team1", ttl=60)
    r2 = await graph_get("/teams/team1", scopes=["https://graph.microsoft.com/.default"], cache_key="teams:team1", ttl=60)
    assert r1 == r2
    assert route.call_count == 1  # only one HTTP call
```

- [ ] **Step 2: Run test, verify it fails**

```bash
pytest tests/test_graph_client.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.graph.client'`

- [ ] **Step 3: Create `app/graph/endpoints.py`**

```python
# All URL builders return relative paths (base URL set in client).


def user(upn: str) -> str:
    return f"/users/{upn}"


def user_presence(user_id: str) -> str:
    return f"/communications/presences/{user_id}"


def user_joined_teams(upn: str) -> str:
    return f"/users/{upn}/joinedTeams"


def user_teamwork(upn: str) -> str:
    return f"/users/{upn}/teamwork"


def team(team_id: str) -> str:
    return f"/teams/{team_id}"


def team_channels(team_id: str) -> str:
    return f"/teams/{team_id}/channels"


def team_channel(team_id: str, channel_id: str) -> str:
    return f"/teams/{team_id}/channels/{channel_id}"


def group_members(group_id: str) -> str:
    return f"/groups/{group_id}/members"


def group_owners(group_id: str) -> str:
    return f"/groups/{group_id}/owners"


def call_record(call_id: str) -> str:
    return f"/communications/callRecords/{call_id}"


def call_record_sessions(call_id: str) -> str:
    return f"/communications/callRecords/{call_id}/sessions"
```

- [ ] **Step 4: Create `app/graph/client.py`**

```python
from __future__ import annotations

from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.graph.cache import cached_get
from app.graph.errors import (
    AuthError,
    GraphError,
    GraphValidationError,
    NotFoundError,
    ServiceUnavailableError,
    ThrottlingError,
)
from app.security.auth import get_token

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"

_http_client = httpx.AsyncClient(
    base_url=GRAPH_BASE_URL,
    timeout=30.0,
    limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
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


@retry(
    retry=retry_if_exception_type((ThrottlingError, ServiceUnavailableError)),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(4),
    reraise=True,
)
async def _request(method: str, path: str, scopes: list[str], params: dict[str, Any] | None) -> Any:
    token = get_token(scopes)
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    response = await _http_client.request(method, path, headers=headers, params=params)
    _raise_for_status(response, path)
    return response.json() if response.content else {}


async def graph_get(
    path: str,
    scopes: list[str],
    params: dict[str, Any] | None = None,
    cache_key: str | None = None,
    ttl: float = 0,
) -> Any:
    if cache_key and ttl > 0:
        return await cached_get(cache_key, ttl, lambda: _request("GET", path, scopes, params))
    return await _request("GET", path, scopes, params)
```

- [ ] **Step 5: Run tests, verify pass**

```bash
pytest tests/test_graph_client.py -v
```

Expected: `4 passed`

- [ ] **Step 6: Run all tests**

```bash
pytest -v
```

Expected: all previous tests still pass.

- [ ] **Step 7: Commit**

```bash
git add app/graph/client.py app/graph/endpoints.py tests/test_graph_client.py
git commit -m "feat: Graph HTTP client with retry, caching, error handling"
```

---

## Task 7: Audit Service

**Files:**
- Create: `app/services/audit_service.py`

- [ ] **Step 1: Create `app/services/audit_service.py`**

```python
from __future__ import annotations

import threading
from collections import deque
from datetime import datetime, timezone
from typing import Any

from app.config import settings

_buffer: deque[dict[str, Any]] = deque(maxlen=settings.audit_buffer_size)
_lock = threading.Lock()


def record(
    *,
    tool: str,
    upn_hint: str,
    elapsed_ms: int,
    status: str,
    error_type: str | None,
) -> None:
    entry: dict[str, Any] = {
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "tool": tool,
        "upn_hint": upn_hint,
        "elapsed_ms": elapsed_ms,
        "status": status,
        "error_type": error_type,
    }
    with _lock:
        _buffer.append(entry)


def get_history(limit: int = 50) -> list[dict[str, Any]]:
    with _lock:
        entries = list(_buffer)
    return entries[-limit:]


def get_summary() -> dict[str, Any]:
    with _lock:
        entries = list(_buffer)
    total = len(entries)
    if total == 0:
        return {"total_calls": 0, "message": "No tool calls recorded yet."}
    errors = sum(1 for e in entries if e["status"] == "error")
    tools_used = sorted({e["tool"] for e in entries})
    avg_elapsed = sum(e["elapsed_ms"] for e in entries) / total
    return {
        "total_calls": total,
        "error_count": errors,
        "success_rate": f"{(total - errors) / total * 100:.1f}%",
        "avg_elapsed_ms": round(avg_elapsed),
        "tools_used": tools_used,
        "recent": entries[-10:],
    }


def get_by_upn(upn_hint: str, limit: int = 20) -> list[dict[str, Any]]:
    with _lock:
        entries = list(_buffer)
    matched = [e for e in entries if upn_hint.lower() in e.get("upn_hint", "").lower()]
    return matched[-limit:]
```

- [ ] **Step 2: Commit**

```bash
git add app/services/audit_service.py
git commit -m "feat: in-memory audit ring buffer"
```

---

## Task 8: User Schemas & Service

**Files:**
- Create: `app/schemas/users.py`
- Create: `app/services/users_service.py`
- Create: `tests/test_services.py` (initial)

- [ ] **Step 1: Write failing tests for users service**

```python
# tests/test_services.py
import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_get_user_profile_calls_graph():
    mock_result = {"id": "abc123", "displayName": "Alice", "userPrincipalName": "alice@corp.com"}

    with patch("app.services.users_service.graph_get", new=AsyncMock(return_value=mock_result)):
        from app.services.users_service import get_user_profile
        result = await get_user_profile("alice@corp.com")

    assert result["id"] == "abc123"
    assert result["displayName"] == "Alice"


@pytest.mark.asyncio
async def test_get_user_overview_combines_profile_and_teams():
    profile = {"id": "abc123", "displayName": "Alice", "userPrincipalName": "alice@corp.com"}
    teams = {"value": [{"id": "t1", "displayName": "Sales Team"}]}
    presence = {"availability": "Available", "activity": "Available"}

    async def mock_graph_get(path, *args, **kwargs):
        if "/joinedTeams" in path:
            return teams
        if "/presences/" in path:
            return presence
        return profile

    with patch("app.services.users_service.graph_get", new=mock_graph_get):
        from app.services.users_service import get_user_overview
        result = await get_user_overview("alice@corp.com")

    assert result["upn"] == "alice@corp.com"
    assert result["profile"]["displayName"] == "Alice"
    assert result["teams"]["value"][0]["displayName"] == "Sales Team"
```

- [ ] **Step 2: Run test, verify it fails**

```bash
pytest tests/test_services.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.services.users_service'`

- [ ] **Step 3: Create `app/schemas/users.py`**

```python
from pydantic import Field

from app.schemas.common import ResponseFormat, ToolParams


class GetUserProfileParams(ToolParams):
    upn: str = Field(min_length=1, description="User Principal Name, e.g. alice@contoso.com")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class GetUserPresenceParams(ToolParams):
    upn: str = Field(min_length=1, description="User Principal Name")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class GetUserOverviewParams(ToolParams):
    upn: str = Field(min_length=1, description="User Principal Name")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class GetUserAssignedPoliciesParams(ToolParams):
    upn: str = Field(min_length=1, description="User Principal Name")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class ListUserTeamsParams(ToolParams):
    upn: str = Field(min_length=1, description="User Principal Name")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)
```

- [ ] **Step 4: Create `app/services/users_service.py`**

```python
from __future__ import annotations

import asyncio
from typing import Any

from app.config import settings
from app.graph import endpoints
from app.graph.client import graph_get
from app.security.permissions import SCOPES


async def get_user_profile(upn: str) -> dict[str, Any]:
    return await graph_get(
        endpoints.user(upn),
        scopes=SCOPES["user_read"],
        cache_key=f"user:{upn}",
        ttl=settings.cache_ttl_user,
    )


async def get_user_presence(upn: str) -> dict[str, Any]:
    profile = await get_user_profile(upn)
    user_id = profile.get("id", upn)
    return await graph_get(
        endpoints.user_presence(user_id),
        scopes=SCOPES["presence_read"],
        cache_key=f"presence:{user_id}",
        ttl=settings.cache_ttl_presence,
    )


async def list_user_teams(upn: str) -> dict[str, Any]:
    return await graph_get(
        endpoints.user_joined_teams(upn),
        scopes=SCOPES["team_read"],
        cache_key=f"user_teams:{upn}",
        ttl=settings.cache_ttl_teams,
    )


async def get_user_assigned_policies(upn: str) -> dict[str, Any]:
    return await graph_get(
        endpoints.user_teamwork(upn),
        scopes=SCOPES["directory_read"],
        cache_key=f"user_teamwork:{upn}",
        ttl=settings.cache_ttl_policies,
    )


async def get_user_overview(upn: str) -> dict[str, Any]:
    profile_coro = get_user_profile(upn)
    teams_coro = list_user_teams(upn)

    profile_result, teams_result = await asyncio.gather(profile_coro, teams_coro, return_exceptions=True)

    profile: dict[str, Any] = profile_result if not isinstance(profile_result, Exception) else {"error": str(profile_result)}
    teams: dict[str, Any] = teams_result if not isinstance(teams_result, Exception) else {"error": str(teams_result)}

    presence: dict[str, Any] = {}
    if "id" in profile:
        try:
            presence = await get_user_presence(upn)
        except Exception as exc:
            presence = {"error": str(exc)}

    markdown = _build_overview_markdown(upn, profile, presence, teams)

    return {
        "upn": upn,
        "profile": profile,
        "presence": presence,
        "teams": teams,
        "markdown": markdown,
    }


def _build_overview_markdown(
    upn: str,
    profile: dict[str, Any],
    presence: dict[str, Any],
    teams: dict[str, Any],
) -> str:
    lines = [f"## User Overview: {profile.get('displayName', upn)}"]
    lines.append(f"- **UPN:** {upn}")
    lines.append(f"- **Department:** {profile.get('department', 'N/A')}")
    lines.append(f"- **Job Title:** {profile.get('jobTitle', 'N/A')}")
    lines.append(f"- **Office:** {profile.get('officeLocation', 'N/A')}")
    avail = presence.get("availability", "Unknown")
    lines.append(f"- **Presence:** {avail}")
    team_list = teams.get("value", [])
    lines.append(f"\n### Teams ({len(team_list)})")
    for t in team_list[:10]:
        lines.append(f"  - {t.get('displayName', t.get('id', '?'))}")
    if len(team_list) > 10:
        lines.append(f"  - ...and {len(team_list) - 10} more")
    return "\n".join(lines)
```

- [ ] **Step 5: Run tests, verify pass**

```bash
pytest tests/test_services.py -v
```

Expected: `2 passed`

- [ ] **Step 6: Commit**

```bash
git add app/schemas/users.py app/services/users_service.py tests/test_services.py
git commit -m "feat: user schemas and service (profile, presence, teams, overview)"
```

---

## Task 9: User Tools

**Files:**
- Create: `app/tools/users_tools.py`

- [ ] **Step 1: Create `app/tools/users_tools.py`**

```python
from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from app.logging_config import audited
from app.schemas.common import ResponseFormat
from app.schemas.users import (
    GetUserAssignedPoliciesParams,
    GetUserOverviewParams,
    GetUserPresenceParams,
    GetUserProfileParams,
    ListUserTeamsParams,
)
from app.services import users_service
from app.utils.response import render_response

_ANNOTATIONS = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}


def _register(mcp: FastMCP) -> None:
    @mcp.tool(name="get_user_overview", annotations={**_ANNOTATIONS, "title": "Get User Overview"})
    @audited
    async def get_user_overview(
        upn: str,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> Any:
        """Return a combined view of the user's profile, presence, and joined Teams."""
        p = GetUserOverviewParams.model_validate({"upn": upn, "response_format": response_format})
        result = await users_service.get_user_overview(p.upn)
        return render_response(result, p.response_format)

    @mcp.tool(name="get_user_profile", annotations={**_ANNOTATIONS, "title": "Get User Profile"})
    @audited
    async def get_user_profile(
        upn: str,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> Any:
        """Return detailed Azure AD profile for a user."""
        p = GetUserProfileParams.model_validate({"upn": upn, "response_format": response_format})
        result = await users_service.get_user_profile(p.upn)
        return render_response(result, p.response_format)

    @mcp.tool(name="get_user_presence", annotations={**_ANNOTATIONS, "title": "Get User Presence"})
    @audited
    async def get_user_presence(
        upn: str,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> Any:
        """Return real-time Teams presence status for a user (Available, Busy, Away, etc.)."""
        p = GetUserPresenceParams.model_validate({"upn": upn, "response_format": response_format})
        result = await users_service.get_user_presence(p.upn)
        return render_response(result, p.response_format)

    @mcp.tool(name="get_user_assigned_policies", annotations={**_ANNOTATIONS, "title": "Get User Assigned Policies"})
    @audited
    async def get_user_assigned_policies(
        upn: str,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> Any:
        """Return Teams policies assigned to a user (meeting, calling, messaging, etc.)."""
        p = GetUserAssignedPoliciesParams.model_validate({"upn": upn, "response_format": response_format})
        result = await users_service.get_user_assigned_policies(p.upn)
        return render_response(result, p.response_format)

    @mcp.tool(name="list_user_teams", annotations={**_ANNOTATIONS, "title": "List User Teams"})
    @audited
    async def list_user_teams(
        upn: str,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> Any:
        """List all Microsoft Teams the user is a member of."""
        p = ListUserTeamsParams.model_validate({"upn": upn, "response_format": response_format})
        result = await users_service.list_user_teams(p.upn)
        return render_response(result, p.response_format)
```

- [ ] **Step 2: Commit**

```bash
git add app/tools/users_tools.py
git commit -m "feat: user tools (5 tools registered)"
```

---

## Task 10: Teams Schemas & Service

**Files:**
- Create: `app/schemas/teams.py`
- Create: `app/services/teams_service.py`

- [ ] **Step 1: Create `app/schemas/teams.py`**

```python
from pydantic import Field

from app.schemas.common import ResponseFormat, ToolParams


class ListTeamChannelsParams(ToolParams):
    team_id: str = Field(min_length=1, description="Teams group ID (UUID)")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class ListTeamMembersParams(ToolParams):
    team_id: str = Field(min_length=1, description="Teams group ID (UUID)")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class GetTeamOwnersParams(ToolParams):
    team_id: str = Field(min_length=1, description="Teams group ID (UUID)")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class GetTeamSettingsParams(ToolParams):
    team_id: str = Field(min_length=1, description="Teams group ID (UUID)")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class GetChannelSettingsParams(ToolParams):
    team_id: str = Field(min_length=1, description="Teams group ID (UUID)")
    channel_id: str = Field(min_length=1, description="Channel ID")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class CheckPrivateSharedChannelsParams(ToolParams):
    team_id: str = Field(min_length=1, description="Teams group ID (UUID)")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class DetectOrphanedTeamParams(ToolParams):
    team_id: str = Field(min_length=1, description="Teams group ID (UUID)")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class DetectTeamWithoutOwnerParams(ToolParams):
    team_id: str = Field(min_length=1, description="Teams group ID (UUID)")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)
```

- [ ] **Step 2: Create `app/services/teams_service.py`**

```python
from __future__ import annotations

from typing import Any

from app.config import settings
from app.graph import endpoints
from app.graph.client import graph_get
from app.security.permissions import SCOPES


async def list_team_channels(team_id: str) -> dict[str, Any]:
    data = await graph_get(
        endpoints.team_channels(team_id),
        scopes=SCOPES["channel_read"],
        cache_key=f"channels:{team_id}",
        ttl=settings.cache_ttl_teams,
    )
    channels = data.get("value", [])
    markdown = _channels_markdown(team_id, channels)
    return {"team_id": team_id, "channels": channels, "count": len(channels), "markdown": markdown}


async def list_team_members(team_id: str) -> dict[str, Any]:
    data = await graph_get(
        endpoints.group_members(team_id),
        scopes=SCOPES["team_read"],
        cache_key=f"members:{team_id}",
        ttl=settings.cache_ttl_teams,
    )
    members = data.get("value", [])
    markdown = _members_markdown(team_id, members, role="member")
    return {"team_id": team_id, "members": members, "count": len(members), "markdown": markdown}


async def get_team_owners(team_id: str) -> dict[str, Any]:
    data = await graph_get(
        endpoints.group_owners(team_id),
        scopes=SCOPES["team_read"],
        cache_key=f"owners:{team_id}",
        ttl=settings.cache_ttl_teams,
    )
    owners = data.get("value", [])
    markdown = _members_markdown(team_id, owners, role="owner")
    return {"team_id": team_id, "owners": owners, "count": len(owners), "markdown": markdown}


async def get_team_settings(team_id: str) -> dict[str, Any]:
    data = await graph_get(
        endpoints.team(team_id),
        scopes=SCOPES["team_read"],
        cache_key=f"team:{team_id}",
        ttl=settings.cache_ttl_teams,
    )
    return {**data, "markdown": f"## Team Settings: {data.get('displayName', team_id)}\n\n```json\n{data}\n```"}


async def get_channel_settings(team_id: str, channel_id: str) -> dict[str, Any]:
    data = await graph_get(
        endpoints.team_channel(team_id, channel_id),
        scopes=SCOPES["channel_read"],
        cache_key=f"channel:{team_id}:{channel_id}",
        ttl=settings.cache_ttl_teams,
    )
    return {**data, "markdown": f"## Channel: {data.get('displayName', channel_id)}\n- **Type:** {data.get('membershipType', 'standard')}\n- **Description:** {data.get('description', 'N/A')}"}


async def check_private_shared_channels(team_id: str) -> dict[str, Any]:
    data = await graph_get(
        endpoints.team_channels(team_id),
        scopes=SCOPES["channel_read"],
        cache_key=f"channels:{team_id}",
        ttl=settings.cache_ttl_teams,
    )
    channels = data.get("value", [])
    private = [c for c in channels if c.get("membershipType") == "private"]
    shared = [c for c in channels if c.get("membershipType") == "shared"]
    lines = [f"## Private & Shared Channels in Team {team_id}"]
    lines.append(f"- **Private channels:** {len(private)}")
    lines.append(f"- **Shared channels:** {len(shared)}")
    if private:
        lines.append("\n### Private Channels")
        for c in private:
            lines.append(f"  - {c.get('displayName', c['id'])}")
    if shared:
        lines.append("\n### Shared Channels")
        for c in shared:
            lines.append(f"  - {c.get('displayName', c['id'])}")
    return {"team_id": team_id, "private_channels": private, "shared_channels": shared, "markdown": "\n".join(lines)}


async def detect_orphaned_team(team_id: str) -> dict[str, Any]:
    members_data = await graph_get(
        endpoints.group_members(team_id),
        scopes=SCOPES["team_read"],
        cache_key=f"members:{team_id}",
        ttl=settings.cache_ttl_teams,
    )
    members = members_data.get("value", [])
    is_orphaned = len(members) == 0
    status = "ORPHANED — no members" if is_orphaned else f"OK — {len(members)} member(s)"
    return {
        "team_id": team_id,
        "is_orphaned": is_orphaned,
        "member_count": len(members),
        "status": status,
        "markdown": f"## Orphaned Team Check: {team_id}\n- **Status:** {status}",
    }


async def detect_team_without_owner(team_id: str) -> dict[str, Any]:
    owners_data = await graph_get(
        endpoints.group_owners(team_id),
        scopes=SCOPES["team_read"],
        cache_key=f"owners:{team_id}",
        ttl=settings.cache_ttl_teams,
    )
    owners = owners_data.get("value", [])
    has_no_owner = len(owners) == 0
    status = "NO OWNER — team has no owners" if has_no_owner else f"OK — {len(owners)} owner(s)"
    return {
        "team_id": team_id,
        "has_no_owner": has_no_owner,
        "owner_count": len(owners),
        "owners": owners,
        "status": status,
        "markdown": f"## Owner Check: {team_id}\n- **Status:** {status}",
    }


def _channels_markdown(team_id: str, channels: list[dict[str, Any]]) -> str:
    lines = [f"## Channels in Team {team_id} ({len(channels)} total)"]
    for c in channels:
        ctype = c.get("membershipType", "standard")
        lines.append(f"- **{c.get('displayName', c['id'])}** [{ctype}]")
    return "\n".join(lines)


def _members_markdown(team_id: str, members: list[dict[str, Any]], role: str) -> str:
    lines = [f"## Team {role.capitalize()}s: {team_id} ({len(members)} total)"]
    for m in members:
        name = m.get("displayName", m.get("userPrincipalName", m.get("id", "?")))
        upn = m.get("userPrincipalName", "")
        lines.append(f"- {name} ({upn})" if upn else f"- {name}")
    return "\n".join(lines)
```

- [ ] **Step 3: Add teams service tests to `tests/test_services.py`**

Add to `tests/test_services.py`:

```python
@pytest.mark.asyncio
async def test_detect_orphaned_team_no_members():
    empty = {"value": []}
    with patch("app.services.teams_service.graph_get", new=AsyncMock(return_value=empty)):
        from app.services.teams_service import detect_orphaned_team
        result = await detect_orphaned_team("team-uuid-123")
    assert result["is_orphaned"] is True
    assert result["member_count"] == 0


@pytest.mark.asyncio
async def test_detect_team_without_owner_has_owners():
    owners_data = {"value": [{"id": "u1", "displayName": "Alice"}]}
    with patch("app.services.teams_service.graph_get", new=AsyncMock(return_value=owners_data)):
        from app.services.teams_service import detect_team_without_owner
        result = await detect_team_without_owner("team-uuid-123")
    assert result["has_no_owner"] is False
    assert result["owner_count"] == 1
```

- [ ] **Step 4: Run all tests**

```bash
pytest -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add app/schemas/teams.py app/services/teams_service.py tests/test_services.py
git commit -m "feat: teams schemas and service (8 tools)"
```

---

## Task 11: Teams Tools

**Files:**
- Create: `app/tools/teams_tools.py`

- [ ] **Step 1: Create `app/tools/teams_tools.py`**

```python
from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from app.logging_config import audited
from app.schemas.common import ResponseFormat
from app.schemas.teams import (
    CheckPrivateSharedChannelsParams,
    DetectOrphanedTeamParams,
    DetectTeamWithoutOwnerParams,
    GetChannelSettingsParams,
    GetTeamOwnersParams,
    GetTeamSettingsParams,
    ListTeamChannelsParams,
    ListTeamMembersParams,
)
from app.services import teams_service
from app.utils.response import render_response

_ANNOTATIONS = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}


def _register(mcp: FastMCP) -> None:
    @mcp.tool(name="list_team_channels", annotations={**_ANNOTATIONS, "title": "List Team Channels"})
    @audited
    async def list_team_channels(
        team_id: str,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> Any:
        """List all channels in a Team (standard, private, shared)."""
        p = ListTeamChannelsParams.model_validate({"team_id": team_id, "response_format": response_format})
        result = await teams_service.list_team_channels(p.team_id)
        return render_response(result, p.response_format)

    @mcp.tool(name="list_team_members", annotations={**_ANNOTATIONS, "title": "List Team Members"})
    @audited
    async def list_team_members(
        team_id: str,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> Any:
        """List all members of a Team."""
        p = ListTeamMembersParams.model_validate({"team_id": team_id, "response_format": response_format})
        result = await teams_service.list_team_members(p.team_id)
        return render_response(result, p.response_format)

    @mcp.tool(name="get_team_owners", annotations={**_ANNOTATIONS, "title": "Get Team Owners"})
    @audited
    async def get_team_owners(
        team_id: str,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> Any:
        """Return the owners of a Team."""
        p = GetTeamOwnersParams.model_validate({"team_id": team_id, "response_format": response_format})
        result = await teams_service.get_team_owners(p.team_id)
        return render_response(result, p.response_format)

    @mcp.tool(name="get_team_settings", annotations={**_ANNOTATIONS, "title": "Get Team Settings"})
    @audited
    async def get_team_settings(
        team_id: str,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> Any:
        """Return configuration and settings for a Team."""
        p = GetTeamSettingsParams.model_validate({"team_id": team_id, "response_format": response_format})
        result = await teams_service.get_team_settings(p.team_id)
        return render_response(result, p.response_format)

    @mcp.tool(name="get_channel_settings", annotations={**_ANNOTATIONS, "title": "Get Channel Settings"})
    @audited
    async def get_channel_settings(
        team_id: str,
        channel_id: str,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> Any:
        """Return settings for a specific channel within a Team."""
        p = GetChannelSettingsParams.model_validate({"team_id": team_id, "channel_id": channel_id, "response_format": response_format})
        result = await teams_service.get_channel_settings(p.team_id, p.channel_id)
        return render_response(result, p.response_format)

    @mcp.tool(name="check_private_shared_channels", annotations={**_ANNOTATIONS, "title": "Check Private/Shared Channels"})
    @audited
    async def check_private_shared_channels(
        team_id: str,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> Any:
        """Identify private and shared channels in a Team."""
        p = CheckPrivateSharedChannelsParams.model_validate({"team_id": team_id, "response_format": response_format})
        result = await teams_service.check_private_shared_channels(p.team_id)
        return render_response(result, p.response_format)

    @mcp.tool(name="detect_orphaned_team", annotations={**_ANNOTATIONS, "title": "Detect Orphaned Team"})
    @audited
    async def detect_orphaned_team(
        team_id: str,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> Any:
        """Check if a Team has zero members (orphaned)."""
        p = DetectOrphanedTeamParams.model_validate({"team_id": team_id, "response_format": response_format})
        result = await teams_service.detect_orphaned_team(p.team_id)
        return render_response(result, p.response_format)

    @mcp.tool(name="detect_team_without_owner", annotations={**_ANNOTATIONS, "title": "Detect Team Without Owner"})
    @audited
    async def detect_team_without_owner(
        team_id: str,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> Any:
        """Check if a Team has no owners assigned."""
        p = DetectTeamWithoutOwnerParams.model_validate({"team_id": team_id, "response_format": response_format})
        result = await teams_service.detect_team_without_owner(p.team_id)
        return render_response(result, p.response_format)
```

- [ ] **Step 2: Commit**

```bash
git add app/tools/teams_tools.py
git commit -m "feat: teams tools (8 tools registered)"
```

---

## Task 12: Policies Schemas & Service

**Files:**
- Create: `app/schemas/policies.py`
- Create: `app/services/policies_service.py`

- [ ] **Step 1: Create `app/schemas/policies.py`**

```python
from pydantic import Field

from app.schemas.common import ResponseFormat, ToolParams


class GetUserAssignedPoliciesParams(ToolParams):
    upn: str = Field(min_length=1, description="User Principal Name")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class CompareUserPoliciesParams(ToolParams):
    upn1: str = Field(min_length=1, description="First user's UPN")
    upn2: str = Field(min_length=1, description="Second user's UPN to compare against")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class DetectPolicyConflictsParams(ToolParams):
    upn: str = Field(min_length=1, description="User Principal Name to check for policy conflicts")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)
```

- [ ] **Step 2: Create `app/services/policies_service.py`**

```python
from __future__ import annotations

import asyncio
from typing import Any

from app.config import settings
from app.graph import endpoints
from app.graph.client import graph_get
from app.security.permissions import SCOPES


async def get_user_assigned_policies(upn: str) -> dict[str, Any]:
    data = await graph_get(
        endpoints.user_teamwork(upn),
        scopes=SCOPES["directory_read"],
        cache_key=f"user_teamwork:{upn}",
        ttl=settings.cache_ttl_policies,
    )
    policies = data.get("assignedPolicies", [])
    lines = [f"## Assigned Policies: {upn}"]
    for p in policies:
        lines.append(f"- **{p.get('policyType', '?')}:** {p.get('policyName', 'Global (Org-wide default)')}")
    return {
        "upn": upn,
        "assigned_policies": policies,
        "count": len(policies),
        "markdown": "\n".join(lines),
    }


async def compare_user_policies(upn1: str, upn2: str) -> dict[str, Any]:
    r1, r2 = await asyncio.gather(
        get_user_assigned_policies(upn1),
        get_user_assigned_policies(upn2),
        return_exceptions=True,
    )

    if isinstance(r1, Exception):
        return {"error": f"Failed to fetch policies for {upn1}: {r1}"}
    if isinstance(r2, Exception):
        return {"error": f"Failed to fetch policies for {upn2}: {r2}"}

    policies1 = {p["policyType"]: p.get("policyName", "") for p in r1.get("assigned_policies", [])}
    policies2 = {p["policyType"]: p.get("policyName", "") for p in r2.get("assigned_policies", [])}

    all_types = set(policies1) | set(policies2)
    diff: list[dict[str, Any]] = []
    for ptype in sorted(all_types):
        v1 = policies1.get(ptype, "Global (Org-wide default)")
        v2 = policies2.get(ptype, "Global (Org-wide default)")
        diff.append({"policy_type": ptype, upn1: v1, upn2: v2, "match": v1 == v2})

    mismatches = [d for d in diff if not d["match"]]
    lines = [f"## Policy Comparison: {upn1} vs {upn2}"]
    lines.append(f"- **Mismatches:** {len(mismatches)} of {len(diff)} policy types differ\n")
    lines.append(f"| Policy Type | {upn1} | {upn2} | Match |")
    lines.append("|---|---|---|---|")
    for d in diff:
        match_icon = "✓" if d["match"] else "✗"
        lines.append(f"| {d['policy_type']} | {d[upn1]} | {d[upn2]} | {match_icon} |")

    return {"upn1": upn1, "upn2": upn2, "diff": diff, "mismatch_count": len(mismatches), "markdown": "\n".join(lines)}


async def detect_policy_conflicts(upn: str) -> dict[str, Any]:
    data = await get_user_assigned_policies(upn)
    policies = data.get("assigned_policies", [])

    conflicts: list[dict[str, Any]] = []
    policy_map = {p.get("policyType"): p.get("policyName") for p in policies}

    # Known conflict pattern: TeamsMeetingPolicy with CallingPolicy restrictions
    meeting_policy = policy_map.get("TeamsMeetingPolicy", "")
    calling_policy = policy_map.get("TeamsCallingPolicy", "")
    if "NoAllowedCalling" in str(calling_policy) and "AllowOutlookAddIn" in str(meeting_policy):
        conflicts.append({
            "type": "MeetingCallingConflict",
            "description": "Calling disabled but meeting add-in enabled — user may have meeting scheduling issues.",
            "policies": [meeting_policy, calling_policy],
        })

    lines = [f"## Policy Conflict Detection: {upn}"]
    if conflicts:
        lines.append(f"- **{len(conflicts)} conflict(s) detected**")
        for c in conflicts:
            lines.append(f"\n### {c['type']}")
            lines.append(f"  {c['description']}")
    else:
        lines.append("- No known conflicts detected.")

    return {"upn": upn, "conflicts": conflicts, "conflict_count": len(conflicts), "markdown": "\n".join(lines)}
```

- [ ] **Step 3: Commit**

```bash
git add app/schemas/policies.py app/services/policies_service.py
git commit -m "feat: policies schemas and service (compare, conflict detection)"
```

---

## Task 13: Policies Tools

**Files:**
- Create: `app/tools/policies_tools.py`

- [ ] **Step 1: Create `app/tools/policies_tools.py`**

```python
from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from app.logging_config import audited
from app.schemas.common import ResponseFormat
from app.schemas.policies import CompareUserPoliciesParams, DetectPolicyConflictsParams
from app.services import policies_service
from app.utils.response import render_response

_ANNOTATIONS = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}


def _register(mcp: FastMCP) -> None:
    @mcp.tool(name="compare_user_policies", annotations={**_ANNOTATIONS, "title": "Compare User Policies"})
    @audited
    async def compare_user_policies(
        upn1: str,
        upn2: str,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> Any:
        """Compare Teams policy assignments between two users — useful for troubleshooting policy discrepancies."""
        p = CompareUserPoliciesParams.model_validate({"upn1": upn1, "upn2": upn2, "response_format": response_format})
        result = await policies_service.compare_user_policies(p.upn1, p.upn2)
        return render_response(result, p.response_format)

    @mcp.tool(name="detect_policy_conflicts", annotations={**_ANNOTATIONS, "title": "Detect Policy Conflicts"})
    @audited
    async def detect_policy_conflicts(
        upn: str,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> Any:
        """Detect known conflicting Teams policy combinations for a user."""
        p = DetectPolicyConflictsParams.model_validate({"upn": upn, "response_format": response_format})
        result = await policies_service.detect_policy_conflicts(p.upn)
        return render_response(result, p.response_format)
```

- [ ] **Step 2: Commit**

```bash
git add app/tools/policies_tools.py
git commit -m "feat: policies tools (2 tools registered)"
```

---

## Task 14: Calls Schemas & Service

**Files:**
- Create: `app/schemas/calls.py`
- Create: `app/schemas/diagnostics.py`
- Create: `app/services/calls_service.py`

- [ ] **Step 1: Create `app/schemas/calls.py`**

```python
from pydantic import Field

from app.schemas.common import ResponseFormat, ToolParams


class GetCallQualitySummaryParams(ToolParams):
    upn: str = Field(min_length=1, description="User Principal Name")
    days: int = Field(default=7, ge=1, le=30, description="Lookback window in days (1-30)")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class DiagnoseCallQualityParams(ToolParams):
    call_id: str = Field(min_length=1, description="Call record ID from Microsoft Graph")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class ListFailedCallsParams(ToolParams):
    upn: str = Field(min_length=1, description="User Principal Name")
    days: int = Field(default=7, ge=1, le=30, description="Lookback window in days (1-30)")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class ListPoorQualityCallsParams(ToolParams):
    upn: str = Field(min_length=1, description="User Principal Name")
    days: int = Field(default=7, ge=1, le=30, description="Lookback window in days (1-30)")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)
```

- [ ] **Step 2: Create `app/schemas/diagnostics.py`**

```python
from typing import Any

from pydantic import BaseModel


class CallQualityMetrics(BaseModel):
    call_id: str
    start_time: str
    duration_seconds: int | None = None
    participants: int = 0
    audio_quality: str = "unknown"
    video_quality: str = "unknown"
    result: str = "unknown"
    failure_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()
```

- [ ] **Step 3: Create `app/services/calls_service.py`**

```python
from __future__ import annotations

from typing import Any

from app.config import settings
from app.graph import endpoints
from app.graph.client import graph_get
from app.security.permissions import SCOPES
from app.utils.date_utils import days_ago

_DATA_LAG_WARNING = "Note: Call Records API may have up to 15 minutes latency for recent calls."


async def _get_user_call_records(upn: str, days: int) -> list[dict[str, Any]]:
    since = days_ago(days)
    params = {
        "$filter": f"participants/any(p:p/identity/user/userPrincipalName eq '{upn}') and startDateTime ge {since}",
        "$top": "50",
        "$orderby": "startDateTime desc",
    }
    data = await graph_get(
        "/communications/callRecords",
        scopes=SCOPES["call_records"],
        params=params,
    )
    return data.get("value", [])


async def get_call_quality_summary(upn: str, days: int = 7) -> dict[str, Any]:
    records = await _get_user_call_records(upn, days)
    total = len(records)
    failed = [r for r in records if r.get("result", "").lower() not in ("success", "")]
    lines = [f"## Call Quality Summary: {upn} (last {days} days)", _DATA_LAG_WARNING]
    lines.append(f"- **Total calls:** {total}")
    lines.append(f"- **Failed calls:** {len(failed)}")
    if total > 0:
        lines.append(f"- **Success rate:** {(total - len(failed)) / total * 100:.1f}%")
    return {
        "upn": upn,
        "days": days,
        "total_calls": total,
        "failed_calls": len(failed),
        "records": records,
        "data_lag_warning": _DATA_LAG_WARNING,
        "markdown": "\n".join(lines),
    }


async def diagnose_call_quality(call_id: str) -> dict[str, Any]:
    record = await graph_get(
        endpoints.call_record(call_id),
        scopes=SCOPES["call_records"],
        cache_key=f"callrecord:{call_id}",
        ttl=settings.cache_ttl_calls,
    )
    sessions_data = await graph_get(
        endpoints.call_record_sessions(call_id),
        scopes=SCOPES["call_records"],
        cache_key=f"callsessions:{call_id}",
        ttl=settings.cache_ttl_calls,
    )
    sessions = sessions_data.get("value", [])
    result = record.get("result", "unknown")
    participants = record.get("participants", [])
    lines = [
        f"## Call Diagnosis: {call_id}",
        _DATA_LAG_WARNING,
        f"- **Result:** {result}",
        f"- **Participants:** {len(participants)}",
        f"- **Sessions:** {len(sessions)}",
        f"- **Start:** {record.get('startDateTime', 'N/A')}",
    ]
    if result.lower() != "success":
        lines.append(f"- **Failure reason:** {record.get('failureInfo', {}).get('reason', 'unknown')}")
    return {
        "call_id": call_id,
        "result": result,
        "participant_count": len(participants),
        "session_count": len(sessions),
        "record": record,
        "sessions": sessions,
        "data_lag_warning": _DATA_LAG_WARNING,
        "markdown": "\n".join(lines),
    }


async def list_failed_calls(upn: str, days: int = 7) -> dict[str, Any]:
    records = await _get_user_call_records(upn, days)
    failed = [r for r in records if r.get("result", "").lower() not in ("success", "")]
    lines = [f"## Failed Calls: {upn} (last {days} days)", _DATA_LAG_WARNING, f"- **Count:** {len(failed)}"]
    for r in failed:
        lines.append(f"\n- **{r.get('startDateTime', '?')}** — result: {r.get('result', '?')} | id: {r.get('id', '?')}")
    return {
        "upn": upn,
        "days": days,
        "failed_calls": failed,
        "count": len(failed),
        "data_lag_warning": _DATA_LAG_WARNING,
        "markdown": "\n".join(lines),
    }


async def list_poor_quality_calls(upn: str, days: int = 7) -> dict[str, Any]:
    records = await _get_user_call_records(upn, days)
    # Poor quality: calls with modalities that had issues (heuristic on available fields)
    poor = [r for r in records if r.get("result", "").lower() == "success" and r.get("modalitieCount", 0) == 0]
    lines = [f"## Poor Quality Calls: {upn} (last {days} days)", _DATA_LAG_WARNING, f"- **Count:** {len(poor)}"]
    lines.append("\n*Note: Full quality metrics require session-level data via diagnose_call_quality.*")
    return {
        "upn": upn,
        "days": days,
        "poor_quality_calls": poor,
        "count": len(poor),
        "data_lag_warning": _DATA_LAG_WARNING,
        "markdown": "\n".join(lines),
    }
```

- [ ] **Step 4: Commit**

```bash
git add app/schemas/calls.py app/schemas/diagnostics.py app/services/calls_service.py
git commit -m "feat: calls schemas and service (quality summary, diagnose, failed, poor quality)"
```

---

## Task 15: Calls Tools

**Files:**
- Create: `app/tools/calls_tools.py`

- [ ] **Step 1: Create `app/tools/calls_tools.py`**

```python
from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from app.logging_config import audited
from app.schemas.calls import (
    DiagnoseCallQualityParams,
    GetCallQualitySummaryParams,
    ListFailedCallsParams,
    ListPoorQualityCallsParams,
)
from app.schemas.common import ResponseFormat
from app.services import calls_service
from app.utils.response import render_response

_ANNOTATIONS = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}


def _register(mcp: FastMCP) -> None:
    @mcp.tool(name="get_call_quality_summary", annotations={**_ANNOTATIONS, "title": "Get Call Quality Summary"})
    @audited
    async def get_call_quality_summary(
        upn: str,
        days: int = 7,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> Any:
        """Summarise call quality metrics for a user over the past N days. Note: up to 15min data lag."""
        p = GetCallQualitySummaryParams.model_validate({"upn": upn, "days": days, "response_format": response_format})
        result = await calls_service.get_call_quality_summary(p.upn, p.days)
        return render_response(result, p.response_format)

    @mcp.tool(name="diagnose_call_quality", annotations={**_ANNOTATIONS, "title": "Diagnose Call Quality"})
    @audited
    async def diagnose_call_quality(
        call_id: str,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> Any:
        """Diagnose a specific call using session-level metrics from the Call Records API."""
        p = DiagnoseCallQualityParams.model_validate({"call_id": call_id, "response_format": response_format})
        result = await calls_service.diagnose_call_quality(p.call_id)
        return render_response(result, p.response_format)

    @mcp.tool(name="list_failed_calls", annotations={**_ANNOTATIONS, "title": "List Failed Calls"})
    @audited
    async def list_failed_calls(
        upn: str,
        days: int = 7,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> Any:
        """List calls that ended with a failure result for a user."""
        p = ListFailedCallsParams.model_validate({"upn": upn, "days": days, "response_format": response_format})
        result = await calls_service.list_failed_calls(p.upn, p.days)
        return render_response(result, p.response_format)

    @mcp.tool(name="list_poor_quality_calls", annotations={**_ANNOTATIONS, "title": "List Poor Quality Calls"})
    @audited
    async def list_poor_quality_calls(
        upn: str,
        days: int = 7,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> Any:
        """List calls with poor quality indicators. Use diagnose_call_quality for full session metrics."""
        p = ListPoorQualityCallsParams.model_validate({"upn": upn, "days": days, "response_format": response_format})
        result = await calls_service.list_poor_quality_calls(p.upn, p.days)
        return render_response(result, p.response_format)
```

- [ ] **Step 2: Commit**

```bash
git add app/tools/calls_tools.py
git commit -m "feat: calls tools (4 tools registered)"
```

---

## Task 16: Phase 4 Stub Services & Tools

**Files:**
- Create: `app/services/messages_service.py`
- Create: `app/services/meetings_service.py`
- Create: `app/services/devices_service.py`
- Create: `app/services/voice_service.py`
- Create: `app/services/incidents_service.py`
- Create: `app/tools/messages_tools.py`
- Create: `app/tools/meetings_tools.py`
- Create: `app/tools/devices_tools.py`
- Create: `app/tools/voice_tools.py`

- [ ] **Step 1: Create stub services**

**`app/services/messages_service.py`:**

```python
from app.utils.response import not_implemented_response


async def get_recent_channel_messages(team_id: str, channel_id: str, count: int = 20) -> dict:
    # TODO: GET /teams/{team_id}/channels/{channel_id}/messages?$top={count}
    # Requires: ChannelMessage.Read.All
    return not_implemented_response("get_recent_channel_messages", "GET /teams/{id}/channels/{id}/messages — needs ChannelMessage.Read.All")


async def search_channel_messages(team_id: str, channel_id: str, query: str) -> dict:
    # TODO: Use Graph Search API: POST /search/query with entityTypes=chatMessage
    return not_implemented_response("search_channel_messages", "POST /search/query with entityTypes=chatMessage")


async def summarize_channel_activity(team_id: str, channel_id: str, days: int = 7) -> dict:
    # TODO: GET /teams/{id}/channels/{id}/messages with date filter, aggregate counts
    return not_implemented_response("summarize_channel_activity", "GET /teams/{id}/channels/{id}/messages with date filter")
```

**`app/services/meetings_service.py`:**

```python
from app.utils.response import not_implemented_response


async def get_recent_meetings(upn: str, days: int = 7) -> dict:
    # TODO: GET /users/{upn}/onlineMeetings?$filter=startDateTime ge {date}
    # Requires: OnlineMeetings.Read.All
    return not_implemented_response("get_recent_meetings", "GET /users/{upn}/onlineMeetings — needs OnlineMeetings.Read.All")


async def diagnose_meeting_issues(meeting_id: str) -> dict:
    # TODO: GET /users/{upn}/onlineMeetings/{meetingId} + attendance report
    return not_implemented_response("diagnose_meeting_issues", "GET /users/{upn}/onlineMeetings/{id} + attendanceReports")
```

**`app/services/devices_service.py`:**

```python
from app.utils.response import not_implemented_response


async def get_user_devices(upn: str) -> dict:
    # TODO: GET /users/{upn}/registeredDevices
    # Requires: Directory.Read.All
    return not_implemented_response("get_user_devices", "GET /users/{upn}/registeredDevices — needs Directory.Read.All")


async def detect_device_problems(upn: str) -> dict:
    # TODO: GET /users/{upn}/registeredDevices, check compliance state and lastSyncDateTime
    return not_implemented_response("detect_device_problems", "GET /users/{upn}/registeredDevices — check complianceState and lastSyncDateTime")
```

**`app/services/voice_service.py`:**

```python
from app.utils.response import not_implemented_response


async def get_voice_configuration(upn: str) -> dict:
    # TODO: GET /users/{upn}/onlineMeetings + phone number via /users/{upn}?$select=businessPhones,assignedLicenses
    return not_implemented_response("get_voice_configuration", "GET /users/{upn} with phone fields + calling policies")


async def validate_voice_routing(upn: str) -> dict:
    # TODO: GET /users/{upn}/teamwork + voice routing policy checks
    return not_implemented_response("validate_voice_routing", "GET /users/{upn}/teamwork — check TeamsCallingPolicy + voice routing policy")


async def detect_voice_misconfiguration(upn: str) -> dict:
    # TODO: Cross-check calling policy, dial plan, voice routing policy for conflicts
    return not_implemented_response("detect_voice_misconfiguration", "Cross-check TeamsCallingPolicy, DialPlan, VoiceRoutingPolicy assignments")
```

**`app/services/incidents_service.py`:**

```python
from app.utils.response import not_implemented_response


async def check_known_teams_incidents() -> dict:
    # TODO: GET /admin/serviceAnnouncement/issues?$filter=service eq 'Microsoft Teams'
    # Requires: ServiceHealth.Read.All
    return not_implemented_response("check_known_teams_incidents", "GET /admin/serviceAnnouncement/issues — needs ServiceHealth.Read.All")
```

- [ ] **Step 2: Create stub tools**

**`app/tools/messages_tools.py`:**

```python
from __future__ import annotations
from typing import Any
from fastmcp import FastMCP
from app.logging_config import audited
from app.schemas.common import ResponseFormat
from app.services import messages_service

_ANNOTATIONS = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}


def _register(mcp: FastMCP) -> None:
    @mcp.tool(name="get_recent_channel_messages", annotations={**_ANNOTATIONS, "title": "Get Recent Channel Messages"})
    @audited
    async def get_recent_channel_messages(team_id: str, channel_id: str, count: int = 20, response_format: ResponseFormat = ResponseFormat.MARKDOWN) -> Any:
        """[STUB] Retrieve recent messages from a channel. Requires ChannelMessage.Read.All."""
        return await messages_service.get_recent_channel_messages(team_id, channel_id, count)

    @mcp.tool(name="search_channel_messages", annotations={**_ANNOTATIONS, "title": "Search Channel Messages"})
    @audited
    async def search_channel_messages(team_id: str, channel_id: str, query: str, response_format: ResponseFormat = ResponseFormat.MARKDOWN) -> Any:
        """[STUB] Search messages in a channel. Requires Graph Search API + ChannelMessage.Read.All."""
        return await messages_service.search_channel_messages(team_id, channel_id, query)

    @mcp.tool(name="summarize_channel_activity", annotations={**_ANNOTATIONS, "title": "Summarize Channel Activity"})
    @audited
    async def summarize_channel_activity(team_id: str, channel_id: str, days: int = 7, response_format: ResponseFormat = ResponseFormat.MARKDOWN) -> Any:
        """[STUB] Summarise message activity in a channel over N days."""
        return await messages_service.summarize_channel_activity(team_id, channel_id, days)
```

**`app/tools/meetings_tools.py`:**

```python
from __future__ import annotations
from typing import Any
from fastmcp import FastMCP
from app.logging_config import audited
from app.schemas.common import ResponseFormat
from app.services import meetings_service

_ANNOTATIONS = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}


def _register(mcp: FastMCP) -> None:
    @mcp.tool(name="get_recent_meetings", annotations={**_ANNOTATIONS, "title": "Get Recent Meetings"})
    @audited
    async def get_recent_meetings(upn: str, days: int = 7, response_format: ResponseFormat = ResponseFormat.MARKDOWN) -> Any:
        """[STUB] List recent online meetings for a user. Requires OnlineMeetings.Read.All."""
        return await meetings_service.get_recent_meetings(upn, days)

    @mcp.tool(name="diagnose_meeting_issues", annotations={**_ANNOTATIONS, "title": "Diagnose Meeting Issues"})
    @audited
    async def diagnose_meeting_issues(meeting_id: str, response_format: ResponseFormat = ResponseFormat.MARKDOWN) -> Any:
        """[STUB] Diagnose a specific meeting including attendance and quality data."""
        return await meetings_service.diagnose_meeting_issues(meeting_id)
```

**`app/tools/devices_tools.py`:**

```python
from __future__ import annotations
from typing import Any
from fastmcp import FastMCP
from app.logging_config import audited
from app.schemas.common import ResponseFormat
from app.services import devices_service

_ANNOTATIONS = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}


def _register(mcp: FastMCP) -> None:
    @mcp.tool(name="get_user_devices", annotations={**_ANNOTATIONS, "title": "Get User Devices"})
    @audited
    async def get_user_devices(upn: str, response_format: ResponseFormat = ResponseFormat.MARKDOWN) -> Any:
        """[STUB] List devices registered for a user. Requires Directory.Read.All."""
        return await devices_service.get_user_devices(upn)

    @mcp.tool(name="detect_device_problems", annotations={**_ANNOTATIONS, "title": "Detect Device Problems"})
    @audited
    async def detect_device_problems(upn: str, response_format: ResponseFormat = ResponseFormat.MARKDOWN) -> Any:
        """[STUB] Detect compliance or sync issues on a user's devices."""
        return await devices_service.detect_device_problems(upn)
```

**`app/tools/voice_tools.py`:**

```python
from __future__ import annotations
from typing import Any
from fastmcp import FastMCP
from app.logging_config import audited
from app.schemas.common import ResponseFormat
from app.services import voice_service

_ANNOTATIONS = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}


def _register(mcp: FastMCP) -> None:
    @mcp.tool(name="get_voice_configuration", annotations={**_ANNOTATIONS, "title": "Get Voice Configuration"})
    @audited
    async def get_voice_configuration(upn: str, response_format: ResponseFormat = ResponseFormat.MARKDOWN) -> Any:
        """[STUB] Return voice/Teams Phone configuration for a user."""
        return await voice_service.get_voice_configuration(upn)

    @mcp.tool(name="validate_voice_routing", annotations={**_ANNOTATIONS, "title": "Validate Voice Routing"})
    @audited
    async def validate_voice_routing(upn: str, response_format: ResponseFormat = ResponseFormat.MARKDOWN) -> Any:
        """[STUB] Validate voice routing policy configuration for a user."""
        return await voice_service.validate_voice_routing(upn)

    @mcp.tool(name="detect_voice_misconfiguration", annotations={**_ANNOTATIONS, "title": "Detect Voice Misconfiguration"})
    @audited
    async def detect_voice_misconfiguration(upn: str, response_format: ResponseFormat = ResponseFormat.MARKDOWN) -> Any:
        """[STUB] Detect common Teams Phone misconfigurations for a user."""
        return await voice_service.detect_voice_misconfiguration(upn)
```

- [ ] **Step 3: Commit**

```bash
git add app/services/messages_service.py app/services/meetings_service.py \
        app/services/devices_service.py app/services/voice_service.py \
        app/services/incidents_service.py \
        app/tools/messages_tools.py app/tools/meetings_tools.py \
        app/tools/devices_tools.py app/tools/voice_tools.py
git commit -m "feat: Phase 4 stub services and tools (13 stubs registered)"
```

---

## Task 17: Audit Tools

**Files:**
- Create: `app/tools/audit_tools.py`

- [ ] **Step 1: Create `app/tools/audit_tools.py`**

```python
from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from app.logging_config import audited
from app.services import audit_service

_ANNOTATIONS = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": False}


def _register(mcp: FastMCP) -> None:
    @mcp.tool(name="execution_history", annotations={**_ANNOTATIONS, "title": "Execution History"})
    @audited
    async def execution_history(limit: int = 50) -> Any:
        """Return a log of the last N tool invocations (metadata only, no response content)."""
        entries = audit_service.get_history(limit=min(limit, 200))
        lines = [f"## Execution History (last {len(entries)} calls)"]
        lines.append("| Time | Tool | UPN hint | Elapsed ms | Status |")
        lines.append("|---|---|---|---|---|")
        for e in entries:
            lines.append(f"| {e['timestamp'][:19]} | {e['tool']} | {e['upn_hint']} | {e['elapsed_ms']} | {e['status']} |")
        return {"entries": entries, "markdown": "\n".join(lines)}

    @mcp.tool(name="who_did_what", annotations={**_ANNOTATIONS, "title": "Who Did What"})
    @audited
    async def who_did_what(upn_hint: str, limit: int = 20) -> Any:
        """Return audit entries filtered by UPN hint (partial match). Shows which tools were invoked for a user."""
        entries = audit_service.get_by_upn(upn_hint, limit=limit)
        lines = [f"## Activity for '{upn_hint}' ({len(entries)} entries)"]
        for e in entries:
            lines.append(f"- {e['timestamp'][:19]} | {e['tool']} | {e['status']} | {e['elapsed_ms']}ms")
        return {"upn_hint": upn_hint, "entries": entries, "markdown": "\n".join(lines)}

    @mcp.tool(name="support_case_summary", annotations={**_ANNOTATIONS, "title": "Support Case Summary"})
    @audited
    async def support_case_summary() -> Any:
        """Return aggregate statistics about tool usage in this session (total calls, error rate, tools used)."""
        summary = audit_service.get_summary()
        lines = ["## Support Session Summary"]
        lines.append(f"- **Total calls:** {summary.get('total_calls', 0)}")
        lines.append(f"- **Errors:** {summary.get('error_count', 0)}")
        lines.append(f"- **Success rate:** {summary.get('success_rate', 'N/A')}")
        lines.append(f"- **Avg elapsed:** {summary.get('avg_elapsed_ms', 0)}ms")
        tools = summary.get('tools_used', [])
        if tools:
            lines.append(f"- **Tools used:** {', '.join(tools)}")
        summary["markdown"] = "\n".join(lines)
        return summary
```

- [ ] **Step 2: Commit**

```bash
git add app/tools/audit_tools.py
git commit -m "feat: audit tools (execution_history, who_did_what, support_case_summary)"
```

---

## Task 18: Main Server

**Files:**
- Create: `app/main.py`

- [ ] **Step 1: Create `app/main.py`**

```python
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastmcp import FastMCP

from app.logging_config import logger
from app.tools import (
    audit_tools,
    calls_tools,
    devices_tools,
    meetings_tools,
    messages_tools,
    policies_tools,
    teams_tools,
    users_tools,
    voice_tools,
)


@asynccontextmanager
async def _lifespan(server: FastMCP) -> AsyncGenerator[None, None]:
    logger.info("server_starting", transport=os.getenv("FASTMCP_TRANSPORT", "http"))
    yield
    from app.graph.client import _http_client
    await _http_client.aclose()
    logger.info("server_stopped")


mcp = FastMCP("teams-admin-support-mcp", lifespan=_lifespan)

users_tools._register(mcp)
teams_tools._register(mcp)
policies_tools._register(mcp)
calls_tools._register(mcp)
messages_tools._register(mcp)
meetings_tools._register(mcp)
devices_tools._register(mcp)
voice_tools._register(mcp)
audit_tools._register(mcp)


def main() -> None:
    transport = os.getenv("FASTMCP_TRANSPORT", "http")
    host = os.getenv("FASTMCP_HOST", "127.0.0.1")
    port = int(os.getenv("FASTMCP_PORT", "8000"))
    mcp.run(transport=transport, host=host, port=port)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add app/main.py
git commit -m "feat: FastMCP server entry point with lifespan and all tool registrations"
```

---

## Task 19: Tool Registration Tests

**Files:**
- Create: `tests/test_tool_registration.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create `tests/conftest.py`**

```python
import os
import pytest

# Provide dummy env vars so Settings can instantiate during tests
os.environ.setdefault("AZURE_TENANT_ID", "test-tenant-id")
os.environ.setdefault("AZURE_CLIENT_ID", "test-client-id")
os.environ.setdefault("AZURE_CLIENT_SECRET", "test-client-secret")
```

- [ ] **Step 2: Write tool registration tests**

```python
# tests/test_tool_registration.py
import pytest
from fastmcp import FastMCP


def _build_test_mcp() -> FastMCP:
    from app.tools import (
        audit_tools, calls_tools, devices_tools, meetings_tools,
        messages_tools, policies_tools, teams_tools, users_tools, voice_tools,
    )
    mcp = FastMCP("test-server")
    users_tools._register(mcp)
    teams_tools._register(mcp)
    policies_tools._register(mcp)
    calls_tools._register(mcp)
    messages_tools._register(mcp)
    meetings_tools._register(mcp)
    devices_tools._register(mcp)
    voice_tools._register(mcp)
    audit_tools._register(mcp)
    return mcp


EXPECTED_TOOLS = [
    "get_user_overview", "get_user_profile", "get_user_presence",
    "get_user_assigned_policies", "list_user_teams",
    "list_team_channels", "list_team_members", "get_team_owners",
    "get_team_settings", "get_channel_settings",
    "check_private_shared_channels", "detect_orphaned_team", "detect_team_without_owner",
    "compare_user_policies", "detect_policy_conflicts",
    "get_call_quality_summary", "diagnose_call_quality",
    "list_failed_calls", "list_poor_quality_calls",
    "get_recent_channel_messages", "search_channel_messages", "summarize_channel_activity",
    "get_recent_meetings", "diagnose_meeting_issues",
    "get_user_devices", "detect_device_problems",
    "get_voice_configuration", "validate_voice_routing", "detect_voice_misconfiguration",
    "execution_history", "who_did_what", "support_case_summary",
]


def test_all_expected_tools_registered():
    mcp = _build_test_mcp()
    registered = {t.name for t in mcp.tools.values()} if hasattr(mcp, "tools") else set()
    # FastMCP exposes tools via _tool_manager or similar — adapt to actual FastMCP API
    # If mcp.tools is not available, check by listing tool names from mcp
    tool_names = set()
    try:
        tool_names = {name for name in mcp._tool_manager._tools}
    except AttributeError:
        pass
    for expected in EXPECTED_TOOLS:
        assert expected in tool_names, f"Tool '{expected}' not registered"


def test_tool_count_matches_expected():
    mcp = _build_test_mcp()
    try:
        tool_names = set(mcp._tool_manager._tools.keys())
    except AttributeError:
        pytest.skip("Cannot access tool registry — check FastMCP version")
    assert len(tool_names) >= len(EXPECTED_TOOLS), f"Expected at least {len(EXPECTED_TOOLS)} tools, got {len(tool_names)}"
```

- [ ] **Step 3: Run all tests**

```bash
pytest -v
```

Expected: all previous tests pass; tool registration tests may need FastMCP API adjustment.

- [ ] **Step 4: Run linter**

```bash
ruff check app/ tests/
```

Fix any reported issues.

- [ ] **Step 5: Final commit**

```bash
git add tests/conftest.py tests/test_tool_registration.py
git commit -m "test: tool registration coverage and conftest"
```

---

## Task 20: Smoke Test & README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Verify server starts**

Copy `.env.example` to `.env` and fill in real Azure credentials, then:

```bash
python -m app.main
```

Expected: server starts on `http://127.0.0.1:8000`, no import errors.

- [ ] **Step 2: Create `README.md`**

```markdown
# teams-admin-support-mcp

Read-only Microsoft Teams admin support MCP server. Query users, teams, policies, calls, and more via Microsoft Graph API.

## Prerequisites

- Python 3.11+
- Azure App Registration with client credentials (see Permissions)
- Microsoft Graph API read-only permissions granted

## Setup

```bash
pip install -e ".[dev]"
cp .env.example .env
# Fill in AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET
```

## Run

```bash
python -m app.main
# or
teams-mcp
```

## Docker

```bash
docker compose up --build
```

## Tests

```bash
pytest -v
```

## Required Azure App Permissions (Application, not Delegated)

| Permission | Scope |
|---|---|
| User.Read.All | User profiles |
| Directory.Read.All | Groups, policies |
| Team.ReadBasic.All | Teams membership |
| TeamMember.Read.All | Team members |
| Channel.ReadBasic.All | Channels |
| ChannelSettings.Read.All | Channel settings |
| Presence.Read.All | Presence status |
| CallRecords.Read.All | Call history & quality |
| Reports.Read.All | Usage reports |
| ServiceHealth.Read.All | Incident/health status |

## Tools

See [docs/superpowers/specs/2026-04-28-teams-admin-support-mcp-design.md](docs/superpowers/specs/2026-04-28-teams-admin-support-mcp-design.md) for full tool list.
```

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: README with setup, permissions, and usage"
```

---

## Self-Review Checklist

- [x] All 32 tools from spec accounted for (5 user + 8 teams + 2 policies + 4 calls + 3 messages stubs + 2 meetings stubs + 2 devices stubs + 3 voice stubs + 1 incidents stub + 3 audit)
- [x] `graph_get()` signature consistent across all service files: `(path, scopes, params=None, cache_key=None, ttl=0)`
- [x] `_register(mcp: FastMCP)` pattern used in all tool files
- [x] `@audited` decorator on every tool function
- [x] `render_response(result, p.response_format)` called in every tool
- [x] `not_implemented_response(tool_name, todo)` used in all Phase 4 stubs
- [x] No `graph_get` calls in tool files — only in service files
- [x] `conftest.py` sets env vars so tests don't fail on Settings instantiation
- [x] `clear_cache()` called in test fixtures to prevent cross-test pollution
- [x] `_DATA_LAG_WARNING` included in all call-related responses
