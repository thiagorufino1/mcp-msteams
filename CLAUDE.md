# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

`teams-admin-support-mcp` — read-only Microsoft Teams admin support MCP server. Lets support/admins query Teams data (users, calls, policies, devices, voice) via Microsoft Graph API. No write operations, ever.

The full spec lives in `teams_admin_support_mcp_prompt.md`.

## Tech Stack

- Python 3.11+, FastMCP
- Microsoft Graph API via `httpx`
- Auth: MSAL client credentials (Entra ID App Registration)
- Validation: `pydantic`, `pydantic-settings`
- Resilience: `tenacity` (retry + backoff, 429 throttling)
- Logging: `structlog` (no tokens/secrets/sensitive data in logs)
- Lint: `ruff`, type-check: `mypy`
- Tests: `pytest`

## Planned Architecture

```
app/
  main.py            # FastMCP server entry point
  config.py          # pydantic-settings env config
  logging_config.py
  security/          # auth.py, permissions.py, input_validation.py
  graph/             # client.py (httpx+MSAL), endpoints.py, errors.py, models.py
  services/          # one file per domain (users, teams, policies, messages, calls, meetings, devices, voice, incidents, audit)
  tools/             # FastMCP tool registrations, thin wrappers over services
  schemas/           # pydantic models (users, teams, calls, diagnostics, common)
  utils/             # date_utils.py, sanitization.py, response.py
tests/
.env.example
pyproject.toml
docker-compose.yml
```

## Key Constraints

- **All tools read-only** — no write, send, create, modify, delete operations
- Graph permissions: `User.Read.All`, `Directory.Read.All`, `Group.Read.All`, `Team.ReadBasic.All`, `TeamMember.Read.All`, `Channel.ReadBasic.All`, `ChannelSettings.Read.All`, `Presence.Read.All`, `CallRecords.Read.All`, `Reports.Read.All`, `ServiceHealth.Read.All`
- Never log tokens, secrets, or sensitive data
- All tool inputs must be validated (pydantic)
- Graph errors handled explicitly (throttling 429, timeouts, structured error responses)
- Audit every tool execution (no sensitive content in audit logs)

## Common Commands

```bash
# Install deps (once pyproject.toml exists)
pip install -e ".[dev]"

# Run MCP server
python -m app.main

# Lint
ruff check .

# Type check
mypy app/

# Tests
pytest

# Single test
pytest tests/path/to/test_file.py::test_name
```

## Graph Client Pattern

`app/graph/client.py` wraps `httpx` with MSAL token acquisition, retry via `tenacity`, timeout config, and 429 backoff. Services import the client; tools import services. Tools never call Graph directly.

## Tool Implementation Note

Call Records API has known limitations (latency, availability). Implement call-related tools with clear TODOs and graceful degradation.
