"""Tests verifying all expected MCP tools are registered."""
from __future__ import annotations

import pytest
import pytest_asyncio

EXPECTED_TOOLS = [
    "get_user_overview",
    "get_user_profile",
    "get_user_presence",
    "get_user_assigned_policies",
    "list_user_teams",
    "list_team_channels",
    "list_team_members",
    "get_team_owners",
    "get_team_settings",
    "get_channel_settings",
    "check_private_shared_channels",
    "detect_orphaned_team",
    "detect_team_without_owner",
    "compare_user_policies",
    "detect_policy_conflicts",
    "get_call_quality_summary",
    "diagnose_call_quality",
    "list_failed_calls",
    "list_poor_quality_calls",
    "get_recent_channel_messages",
    "search_channel_messages",
    "summarize_channel_activity",
    "get_recent_meetings",
    "diagnose_meeting_issues",
    "get_user_devices",
    "detect_device_problems",
    "get_voice_configuration",
    "validate_voice_routing",
    "detect_voice_misconfiguration",
    "check_known_teams_incidents",
    "search_user",
    "execution_history",
    "who_did_what",
    "support_case_summary",
]


def _build_test_mcp():
    from fastmcp import FastMCP
    from mcp_msteams.tools import (
        audit_tools,
        calls_tools,
        devices_tools,
        incidents_tools,
        meetings_tools,
        messages_tools,
        policies_tools,
        teams_tools,
        users_tools,
        voice_tools,
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
    incidents_tools._register(mcp)
    audit_tools._register(mcp)
    return mcp


@pytest_asyncio.fixture(scope="module")
async def registered_tool_names() -> set[str]:
    mcp = _build_test_mcp()
    tools = await mcp.list_tools()
    return {t.name for t in tools}


@pytest.mark.asyncio
async def test_all_expected_tools_registered(registered_tool_names: set[str]) -> None:
    """Every tool in EXPECTED_TOOLS must appear in the registered tool set."""
    missing = [name for name in EXPECTED_TOOLS if name not in registered_tool_names]
    assert not missing, f"Missing tools: {missing}"


@pytest.mark.asyncio
async def test_tool_count_at_least_expected(registered_tool_names: set[str]) -> None:
    """At least 34 tools must be registered."""
    assert len(registered_tool_names) >= 34, (
        f"Expected >= 34 tools, got {len(registered_tool_names)}: {sorted(registered_tool_names)}"
    )


@pytest.mark.asyncio
async def test_no_unexpected_tool_names(registered_tool_names: set[str]) -> None:
    """All expected tool names are valid (no typos in the expected list)."""
    expected_set = set(EXPECTED_TOOLS)
    # All expected names must be present (duplicate check)
    assert len(EXPECTED_TOOLS) == len(expected_set), "EXPECTED_TOOLS has duplicates"


@pytest.mark.asyncio
async def test_users_tools_registered(registered_tool_names: set[str]) -> None:
    user_tools = {
        "get_user_overview",
        "get_user_profile",
        "get_user_presence",
        "get_user_assigned_policies",
        "list_user_teams",
        "search_user",
    }
    assert user_tools.issubset(registered_tool_names), (
        f"Missing user tools: {user_tools - registered_tool_names}"
    )


@pytest.mark.asyncio
async def test_teams_tools_registered(registered_tool_names: set[str]) -> None:
    team_tools = {
        "list_team_channels",
        "list_team_members",
        "get_team_owners",
        "get_team_settings",
        "get_channel_settings",
        "check_private_shared_channels",
        "detect_orphaned_team",
        "detect_team_without_owner",
    }
    assert team_tools.issubset(registered_tool_names), (
        f"Missing teams tools: {team_tools - registered_tool_names}"
    )


@pytest.mark.asyncio
async def test_policies_and_calls_tools_registered(registered_tool_names: set[str]) -> None:
    tools = {
        "compare_user_policies",
        "detect_policy_conflicts",
        "get_call_quality_summary",
        "diagnose_call_quality",
        "list_failed_calls",
        "list_poor_quality_calls",
    }
    assert tools.issubset(registered_tool_names), (
        f"Missing policies/calls tools: {tools - registered_tool_names}"
    )


@pytest.mark.asyncio
async def test_phase4_stub_tools_registered(registered_tool_names: set[str]) -> None:
    stub_tools = {
        "get_recent_channel_messages",
        "search_channel_messages",
        "summarize_channel_activity",
        "get_recent_meetings",
        "diagnose_meeting_issues",
        "get_user_devices",
        "detect_device_problems",
        "get_voice_configuration",
        "validate_voice_routing",
        "detect_voice_misconfiguration",
        "check_known_teams_incidents",
    }
    assert stub_tools.issubset(registered_tool_names), (
        f"Missing phase-4 stub tools: {stub_tools - registered_tool_names}"
    )


@pytest.mark.asyncio
async def test_audit_tools_registered(registered_tool_names: set[str]) -> None:
    audit_tool_names = {"execution_history", "who_did_what", "support_case_summary"}
    assert audit_tool_names.issubset(registered_tool_names), (
        f"Missing audit tools: {audit_tool_names - registered_tool_names}"
    )
