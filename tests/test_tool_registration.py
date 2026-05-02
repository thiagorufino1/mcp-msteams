"""Tests verifying currently exposed MCP tools are registered."""
from __future__ import annotations

import pytest
import pytest_asyncio

EXPECTED_TOOLS = [
    "get_user_overview",
    "get_user_profile",
    "get_user_presence",
    "get_user_assigned_policies",
    "list_user_teams",
    "search_user",
    "list_team_channels",
    "list_team_members",
    "get_team_owners",
    "get_team_settings",
    "get_channel_settings",
    "check_private_shared_channels",
    "detect_orphaned_team",
    "detect_team_without_owner",
    "list_all_teams",
    "get_tenant_teams_stats",
    "list_orphaned_teams",
    "list_teams_without_members",
    "list_teams_by_member_count",
    "get_call_quality_summary",
    "diagnose_call_quality",
    "list_failed_calls",
    "get_recent_meetings",
    "get_meeting_participants",
    "get_user_activity_report",
    "check_known_teams_incidents",
    "get_teams_incident_detail",
]


def _build_test_mcp():
    from fastmcp import FastMCP
    from mcp_msteams.tools import (
        calls_tools,
        incidents_tools,
        meetings_tools,
        reports_tools,
        teams_tools,
        users_tools,
    )

    mcp = FastMCP("test-server")
    users_tools._register(mcp)
    teams_tools._register(mcp)
    calls_tools._register(mcp)
    meetings_tools._register(mcp)
    reports_tools._register(mcp)
    incidents_tools._register(mcp)
    return mcp


@pytest_asyncio.fixture(scope="module")
async def registered_tool_names() -> set[str]:
    mcp = _build_test_mcp()
    tools = await mcp.list_tools()
    return {t.name for t in tools}


@pytest.mark.asyncio
async def test_all_expected_tools_registered(registered_tool_names: set[str]) -> None:
    missing = [name for name in EXPECTED_TOOLS if name not in registered_tool_names]
    assert not missing, f"Missing tools: {missing}"


@pytest.mark.asyncio
async def test_tool_count_matches_expected(registered_tool_names: set[str]) -> None:
    assert len(registered_tool_names) == len(EXPECTED_TOOLS), (
        f"Expected {len(EXPECTED_TOOLS)} tools, got {len(registered_tool_names)}: "
        f"{sorted(registered_tool_names)}"
    )


@pytest.mark.asyncio
async def test_no_duplicate_expected_tool_names() -> None:
    assert len(EXPECTED_TOOLS) == len(set(EXPECTED_TOOLS)), "EXPECTED_TOOLS has duplicates"
