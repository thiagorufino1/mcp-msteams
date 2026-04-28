# mcp-msteams

Read-only Microsoft Teams admin support MCP server. Query users, teams, policies, calls, and more via Microsoft Graph API. Designed for support/admin diagnostics — zero write operations.

## Prerequisites

- Python 3.11+
- Azure App Registration with client credentials (Entra ID)
- Microsoft Graph API read-only permissions granted (see below)

## Setup

```bash
pip install -e ".[dev]"
cp .env.example .env
# Fill in AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET
```

## Run

```bash
python -m mcp_msteams.server
# or via installed entry point:
mcp-msteams
```

## Tests

```bash
pytest -v
```

## Required Azure App Registration Permissions (Application, not Delegated)

| Permission | Purpose |
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

## Tool Inventory

### Phase 1 — Users (fully implemented)
- `get_user_overview` — Profile + presence + joined teams in one call
- `get_user_profile` — Full Azure AD profile
- `get_user_presence` — Real-time Teams presence
- `get_user_assigned_policies` — Assigned Teams policies
- `list_user_teams` — All teams the user belongs to

### Phase 2 — Teams & Channels (fully implemented)
- `list_team_channels`, `list_team_members`, `get_team_owners`
- `get_team_settings`, `get_channel_settings`
- `check_private_shared_channels`
- `detect_orphaned_team`, `detect_team_without_owner`

### Phase 3 — Policies & Calls (fully implemented)
- `compare_user_policies`, `detect_policy_conflicts`
- `get_call_quality_summary`, `diagnose_call_quality`
- `list_failed_calls`, `list_poor_quality_calls`

### Phase 4 — Stubs (ready for implementation)
- Messages: `get_recent_channel_messages`, `search_channel_messages`, `summarize_channel_activity`
- Meetings: `get_recent_meetings`, `diagnose_meeting_issues`
- Devices: `get_user_devices`, `detect_device_problems`
- Voice: `get_voice_configuration`, `validate_voice_routing`, `detect_voice_misconfiguration`
- Incidents: `check_known_teams_incidents`

### Audit
- `execution_history`, `who_did_what`, `support_case_summary`

## Known Limitations

- **Call Records API**: up to 15 minutes latency for recent calls
- **Presence API**: requires Presence.Read.All — not available on all license tiers
- Phase 4 tools return `{"status": "not_implemented", "todo": "..."}` until implemented
