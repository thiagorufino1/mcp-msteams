# Design: teams-admin-support-mcp

**Date:** 2026-04-28  
**Status:** Approved  
**Transport:** HTTP/SSE  
**Cache:** TTL (all domains)  
**Priority:** User-first, then Teams, Policies, Calls, rest as stubs

---

## 1. Architecture & Folder Structure

```
mcp-teams/
├── app/
│   ├── main.py                  # FastMCP server, lifespan, _register calls
│   ├── config.py                # pydantic-settings: tenant, client_id, secret, scopes, timeouts, TTLs
│   ├── logging_config.py        # structlog + trace_id per invocation, _audited decorator
│   ├── security/
│   │   ├── auth.py              # MSAL ConfidentialClientApplication, token cache, refresh
│   │   ├── permissions.py       # scope constants, per-tool scope mapping
│   │   └── input_validation.py  # sanitize UPNs, IDs, date ranges
│   ├── graph/
│   │   ├── client.py            # httpx.AsyncClient + MSAL token injection, retry, 429 backoff
│   │   ├── endpoints.py         # Graph URL constants (no magic strings in services)
│   │   ├── errors.py            # GraphError, ThrottlingError, NotFoundError
│   │   └── cache.py             # TTL cache (asyncio.Lock per key, prevents stampede)
│   ├── services/
│   │   ├── users_service.py
│   │   ├── teams_service.py
│   │   ├── policies_service.py
│   │   ├── messages_service.py
│   │   ├── calls_service.py
│   │   ├── meetings_service.py
│   │   ├── devices_service.py
│   │   ├── voice_service.py
│   │   ├── incidents_service.py
│   │   └── audit_service.py
│   ├── tools/
│   │   ├── users_tools.py
│   │   ├── teams_tools.py
│   │   ├── policies_tools.py
│   │   ├── messages_tools.py
│   │   ├── calls_tools.py
│   │   ├── meetings_tools.py
│   │   ├── devices_tools.py
│   │   ├── voice_tools.py
│   │   └── audit_tools.py
│   ├── schemas/
│   │   ├── common.py            # ToolParams base, ResponseFormat enum
│   │   ├── users.py
│   │   ├── teams.py
│   │   ├── policies.py
│   │   ├── calls.py
│   │   └── diagnostics.py
│   └── utils/
│       ├── date_utils.py        # ISO 8601 helpers, Graph date filters
│       ├── sanitization.py      # mask PII in logs
│       └── response.py          # _render_response(result, fmt)
├── tests/
│   ├── test_graph_client.py
│   ├── test_auth.py
│   ├── test_cache.py
│   ├── test_services.py
│   ├── test_tool_registration.py
│   └── test_sanitization.py
├── docs/superpowers/specs/
├── .env.example
├── pyproject.toml
├── docker-compose.yml
└── CLAUDE.md
```

**Key design decisions:**
- `security/auth.py` owns MSAL singleton — graph client calls `get_token()`, never handles secrets directly
- `graph/cache.py` separate from main cache — Graph-specific TTLs and keys
- `services/` layer isolates Graph from tools — tools never import `graph/client.py` directly
- `schemas/` split by domain for maintainability

---

## 2. Data Flow

```
Tool call (LLM)
    │
    ▼
tools/*_tools.py::_register → tool_fn(params)
    │  validate input (pydantic schema)
    │  audit log: tool_invoked, trace_id
    ▼
services/*_service.py::domain_fn(validated_params)
    │  build Graph URLs via endpoints.py constants
    │  parallel fetch with asyncio.gather() where applicable
    ▼
graph/client.py::get(path, params, ttl, cache_key)
    │  check graph/cache.py → hit: return cached
    │  miss: get_token() from security/auth.py
    │         inject Authorization: Bearer header
    │         httpx.AsyncClient.request()
    │         429 → read Retry-After, sleep, retry (tenacity)
    │         5xx → exponential backoff (tenacity)
    │         4xx → raise typed GraphError subclass
    │         store result in cache with TTL
    ▼
service assembles response dict
    ▼
tool calls utils/response.py::_render_response(result, fmt)
    │  fmt=json  → return dict
    │  fmt=markdown → return formatted string
    ▼
audit log: tool_completed, elapsed_ms, status=ok
```

### MSAL Token Flow

```
security/auth.py
└── ConfidentialClientApplication (singleton, created at startup)
    └── acquire_token_for_client(scopes)
        └── MSAL in-memory token cache → auto-refresh before expiry
            └── graph/client.py calls get_token() → always valid Bearer
                └── token NEVER logged (sanitization.py intercepts)
```

### Cache TTLs

| Domain | TTL |
|---|---|
| User profile | 5 min (300s) |
| Team/channel settings | 10 min (600s) |
| Policies | 15 min (900s) |
| Presence | 30 sec |
| Call records | 2 min (120s) |
| Incidents | 5 min (300s) |
| Devices | 5 min (300s) |

---

## 3. Tool Inventory & Implementation Priority

### Phase 1 — Fully implemented (User foundation)

| Tool | Graph Endpoint | Scope |
|---|---|---|
| `get_user_overview` | `/users/{upn}` + presence + policies | User.Read.All, Presence.Read.All |
| `get_user_profile` | `/users/{upn}` | User.Read.All |
| `get_user_presence` | `/communications/presences/{id}` | Presence.Read.All |
| `get_user_assigned_policies` | `/users/{upn}/teamwork` + policy endpoints | Directory.Read.All |
| `list_user_teams` | `/users/{upn}/joinedTeams` | Team.ReadBasic.All |

### Phase 2 — Fully implemented (Teams/Channels)

| Tool | Graph Endpoint |
|---|---|
| `list_team_channels` | `/teams/{id}/channels` |
| `list_team_members` | `/groups/{id}/members` |
| `get_team_owners` | `/groups/{id}/owners` |
| `get_team_settings` | `/teams/{id}` |
| `get_channel_settings` | `/teams/{id}/channels/{channelId}` |
| `check_private_shared_channels` | `/teams/{id}/channels` filtered by membershipType |
| `detect_orphaned_team` | `/groups/{id}/members` → count=0 |
| `detect_team_without_owner` | `/groups/{id}/owners` → count=0 |

### Phase 3 — Fully implemented (Policies & Call Quality)

| Tool | Notes |
|---|---|
| `compare_user_policies` | Diff two users' effective policies |
| `detect_policy_conflicts` | Flag conflicting assignments |
| `get_call_quality_summary` | CallRecords API aggregate |
| `diagnose_call_quality` | Per-session metrics |
| `list_failed_calls` | Filter by result != success |
| `list_poor_quality_calls` | Filter by quality scores |

### Phase 4 — Functional stubs with clear TODOs

Stub contract: tool is registered with correct signature and pydantic validation. Returns `{"status": "not_implemented", "tool": "<name>", "todo": "<Graph endpoint + scope needed>"}`. No placeholder logic — just the shell ready to fill in.

```
# Messages
get_recent_channel_messages, search_channel_messages, summarize_channel_activity

# Calls
find_user_calls, get_call_record, get_call_sessions, get_call_participants

# Meetings
get_recent_meetings, diagnose_meeting_issues

# Devices
get_user_devices, detect_device_problems

# Voice
get_voice_configuration, validate_voice_routing, detect_voice_misconfiguration

# Incidents
check_known_teams_incidents

# Audit (in-memory, no Graph)
execution_history, who_did_what, support_case_summary
```

---

## 4. Security & Error Handling

### Security Principles

- MSAL singleton in `auth.py` — token never exposed to tools or services
- `sanitization.py` masks: UPNs → `u***@domain.com`, JWT tokens → `[TOKEN]`, secrets → `[REDACTED]`
- All tool inputs validated via pydantic before any Graph call
- Scope allowlist per tool in `permissions.py`
- Tenant allowlist in `config.py` — rejects unexpected tenant IDs
- Principle of least privilege: only read-only Graph permissions requested

### Error Hierarchy

```
GraphError (base)
├── ThrottlingError (429) → retry with Retry-After header value
├── NotFoundError (404)   → structured response, no stack trace to LLM
├── AuthError (401/403)   → clear message, check app registration scopes
├── GraphValidationError (400) → surface invalid params back to tool
└── ServiceUnavailableError (503) → retry with backoff, then degrade gracefully
```

### Tenacity Retry Config

```python
@retry(
    retry=retry_if_exception_type((ThrottlingError, ServiceUnavailableError)),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(4),
    reraise=True,
)
```

### Audit Ring Buffer

- Max 500 entries in memory (configurable via env `AUDIT_BUFFER_SIZE`)
- Entry fields: `{timestamp, tool, upn_hint, elapsed_ms, status, error_type}`
- No Graph response content stored — metadata only
- `execution_history` and `who_did_what` tools query this buffer
- `support_case_summary` aggregates last N entries into a structured report

### Log Sanitization Rules

- Any string matching `eyJ` prefix (JWT) → `[TOKEN]`
- UPN regex `\S+@\S+\.\S+` → `u***@domain.com` in log fields
- Azure client secret patterns → `[REDACTED]`

---

## 5. Testing & Deployment

### Test Strategy

| File | Covers |
|---|---|
| `test_graph_client.py` | httpx mock: 200, 429 retry, 404, 503 |
| `test_auth.py` | MSAL mock: token acquisition, cache hit |
| `test_cache.py` | TTL expiry, lock prevents stampede |
| `test_services.py` | Service logic with mocked graph client |
| `test_tool_registration.py` | All tools registered, `readOnlyHint=True` |
| `test_sanitization.py` | UPN masking, JWT masking |

No integration tests requiring real Graph credentials. Stack: `pytest`, `pytest-asyncio`, `respx`.

### pyproject.toml

```toml
[project]
name = "teams-admin-support-mcp"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastmcp",
    "httpx",
    "msal",
    "pydantic",
    "pydantic-settings",
    "tenacity",
    "structlog",
]

[project.optional-dependencies]
dev = ["pytest", "pytest-asyncio", "respx", "ruff", "mypy"]

[project.scripts]
teams-mcp = "app.main:main"

[tool.pytest.ini_options]
asyncio_mode = "strict"

[tool.ruff]
line-length = 100
target-version = "py311"
```

### docker-compose.yml

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

### .env.example

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

---

## 6. Known Limitations

- **Call Records API**: up to 15-minute latency for new records. Call tools display `data_lag_warning` in response.
- **Presence API**: requires `Presence.Read.All` — not available on all tenant license tiers.
- **Policy APIs**: some Teams policy endpoints require `TeamworkDevice.Read.All` or additional admin consent.
- **Message read**: `ChannelMessage.Read.All` requires additional consent beyond base read-only scope set.

---

## Reference

- Based on `mcp-meraki` patterns: `_register(mcp)`, `_audited` decorator, TTL cache with asyncio.Lock, dual JSON/Markdown responses
- Spec: `teams_admin_support_mcp_prompt.md`
- Graph API docs: https://learn.microsoft.com/en-us/graph/api/overview
