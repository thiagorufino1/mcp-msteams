# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

`mcp-msteams` — read-only Microsoft Teams admin support MCP server. Lets support/admins query Teams data (users, calls, policies, devices, voice) via Microsoft Graph API. No write operations, ever.

## Tech Stack

- Python 3.11+, FastMCP
- Microsoft Graph API via `httpx`
- Auth: MSAL client credentials (Entra ID App Registration)
- Validation: `pydantic`, `pydantic-settings`
- Resilience: `tenacity` (retry + backoff, 429 throttling) — shared `_GRAPH_RETRY` decorator in `graph/client.py`
- Logging: `structlog` (no tokens/secrets/sensitive data in logs)
- Lint: `ruff`, type-check: `mypy`
- Tests: `pytest` + `respx` (httpx mock)

## Architecture

```
mcp_msteams/
  server.py          # FastMCP entry point — lifespan, all _register() calls
  config.py          # pydantic-settings env config (Settings singleton)
  logging_config.py  # structlog setup, @audited decorator, UPN masking
  security/
    auth.py          # MSAL ConfidentialClientApplication singleton, get_token()
    permissions.py   # SCOPES dict (all map to .default for client credentials)
    input_validation.py  # validate_upn(), validate_uuid(), validate_days()
  graph/
    client.py        # graph_get(), graph_get_all() — httpx + MSAL + tenacity
    endpoints.py     # URL builder functions (URL-encodes all path params)
    errors.py        # GraphError hierarchy (Throttling, NotFound, Auth, etc.)
    cache.py         # TTL cache with asyncio.Lock per key (stampede prevention)
  services/          # one file per domain — only layer that calls graph_get
    users_service.py, teams_service.py, policies_service.py, calls_service.py
    messages_service.py, meetings_service.py, devices_service.py
    voice_service.py, incidents_service.py, audit_service.py
  tools/             # thin wrappers — _register(mcp) pattern, @audited, try/except
    users_tools.py, teams_tools.py, policies_tools.py, calls_tools.py
    messages_tools.py, meetings_tools.py, devices_tools.py
    voice_tools.py, incidents_tools.py, audit_tools.py
  schemas/           # pydantic ToolParams per domain
    common.py, users.py, teams.py, policies.py, calls.py
  utils/
    sanitization.py  # mask_upn(), mask_token(), sanitize_log_value()
    date_utils.py    # utc_now(), days_ago(), graph_date_filter()
    response.py      # render_response(), graph_error_response(), not_implemented_response()
tests/
.env.example
pyproject.toml
```

## Key Constraints

- **All tools read-only** — no write, send, create, modify, delete operations
- Graph permissions: `User.Read.All`, `Directory.Read.All`, `Group.Read.All`, `Team.ReadBasic.All`, `TeamMember.Read.All`, `Channel.ReadBasic.All`, `ChannelSettings.Read.All`, `Presence.Read.All`, `CallRecords.Read.All`, `Reports.Read.All`, `ServiceHealth.Read.All`
- Never log tokens, secrets, or sensitive data
- All tool inputs validated via pydantic before any Graph call
- Graph errors caught at tool boundary → `graph_error_response()` with LLM-actionable guidance
- Audit every tool execution via `@audited` decorator (no sensitive content in audit logs)

## Common Commands

```bash
# Install
pip install -e ".[dev]"

# Run MCP server
python -m mcp_msteams.server
# or via entry point:
mcp-msteams

# Lint
ruff check mcp_msteams/ tests/

# Type check
mypy mcp_msteams/

# Tests
pytest

# Single test
pytest tests/path/to/test_file.py::test_name
```

## Graph Client Pattern

`mcp_msteams/graph/client.py` owns all HTTP logic:
- `graph_get(path, scopes, params, cache_key, ttl, extra_headers)` — single page, optional cache
- `graph_get_all(path, scopes, params, max_pages, extra_headers)` — auto-paginates via `@odata.nextLink`
- Both use shared `_GRAPH_RETRY` decorator (tenacity, 4 attempts, exponential backoff)
- `extra_headers` supports Graph endpoints needing special headers (e.g. `ConsistencyLevel: eventual`)

**Layer rule:** Services call `graph_get`/`graph_get_all`. Tools call services. Tools never call Graph directly.

## Tool Pattern

Every tool in `tools/` follows this exact structure:

```python
@mcp.tool(name="tool_name", annotations={**_ANNOTATIONS, "title": "..."})
@audited
async def tool_name(param: str, response_format: ResponseFormat = ResponseFormat.MARKDOWN) -> Any:
    """Rich docstring: USE when / DON'T USE when / FLOW / REQUIRES."""
    p = SomeParams.model_validate({"param": param, "response_format": response_format})
    try:
        result = await some_service.some_function(p.param)
    except Exception as exc:
        result = graph_error_response(exc, context=f"context '{p.param}'")
    return render_response(result, p.response_format)
```

## Call Records API Note

Up to 15-minute data latency. All call tools include `data_lag_warning` in response. Phase 4 tools (messages, meetings, devices, voice, incidents) return `not_implemented_response()` — ready for expansion.
