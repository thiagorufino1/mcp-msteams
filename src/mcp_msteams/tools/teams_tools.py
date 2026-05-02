from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from mcp_msteams.logging_config import audited
from mcp_msteams.schemas.common import ResponseFormat
from mcp_msteams.schemas.teams import (
    CheckPrivateSharedChannelsParams,
    DetectOrphanedTeamParams,
    DetectTeamWithoutOwnerParams,
    GetChannelSettingsParams,
    GetTeamOwnersParams,
    GetTeamSettingsParams,
    GetTenantTeamsStatsParams,
    ListAllTeamsParams,
    ListOrphanedTeamsParams,
    ListTeamChannelsParams,
    ListTeamMembersParams,
    ListTeamsByMemberCountParams,
    ListTeamsWithoutMembersParams,
)
from mcp_msteams.services import teams_service
from mcp_msteams.utils.response import render_response, graph_error_response

_ANNOTATIONS = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}


def _register(mcp: FastMCP) -> None:

    # ── per-team tools ────────────────────────────────────────────────────────

    @mcp.tool(name="list_team_channels", annotations={**_ANNOTATIONS, "title": "List Team Channels"})
    @audited
    async def list_team_channels(
        team_id: str,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> Any:
        """List all channels in a Team (standard, private, shared).

        USE when: the user wants to see channels in a specific group.
        PARAMETERS:
          - team_id: group GUID (e.g. '7932e3f3-67f1-4ede-809e-dc943c43cab5').
                     Obtain via list_user_teams. NEVER pass a display name.
        """
        p = ListTeamChannelsParams.model_validate({"team_id": team_id, "response_format": response_format})
        try:
            result = await teams_service.list_team_channels(p.team_id)
        except Exception as exc:
            result = graph_error_response(exc, context=f"channels in team '{p.team_id}'")
        return render_response(result, p.response_format)

    @mcp.tool(name="list_team_members", annotations={**_ANNOTATIONS, "title": "List Team Members"})
    @audited
    async def list_team_members(
        team_id: str,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> Any:
        """List all members of a specific Team.

        USE when: the user wants to see who is in a given group.
        PARAMETERS:
          - team_id: group GUID. Obtain via list_user_teams.
                     NEVER pass a display name — always the UUID.
        NOTE: For member counts across ALL tenant teams, use list_all_teams(include_counts=True)
        or get_tenant_teams_stats instead.
        """
        p = ListTeamMembersParams.model_validate({"team_id": team_id, "response_format": response_format})
        try:
            result = await teams_service.list_team_members(p.team_id)
        except Exception as exc:
            result = graph_error_response(exc, context=f"members of team '{p.team_id}'")
        return render_response(result, p.response_format)

    @mcp.tool(name="get_team_owners", annotations={**_ANNOTATIONS, "title": "Get Team Owners"})
    @audited
    async def get_team_owners(
        team_id: str,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> Any:
        """Return the owners (proprietarios) of a specific Team.

        CRITICAL: team_id MUST be the group GUID (UUID), NOT a display name.
        Common mistake: passing 'Endpoint Management' causes API error 400.
        CORRECT FLOW:
          1. Call list_user_teams to get the GUID from the results.
          2. Pass only the UUID here (e.g. '7932e3f3-67f1-4ede-809e-dc943c43cab5').
             Reuse the GUID already obtained in this conversation — do not search again.
        For tenant-wide orphaned teams (no owners), use list_orphaned_teams instead.
        """
        p = GetTeamOwnersParams.model_validate({"team_id": team_id, "response_format": response_format})
        try:
            result = await teams_service.get_team_owners(p.team_id)
        except Exception as exc:
            result = graph_error_response(exc, context=f"owners of team '{p.team_id}'")
        return render_response(result, p.response_format)

    @mcp.tool(name="get_team_settings", annotations={**_ANNOTATIONS, "title": "Get Team Settings"})
    @audited
    async def get_team_settings(
        team_id: str,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> Any:
        """Return configuration and settings for a specific Team.

        CRITICAL: team_id MUST be the group GUID (UUID), NOT a display name.
        Common mistake: passing a team name causes API error 400.
        CORRECT FLOW:
          1. If you already obtained the GUID in this conversation (e.g. from
             list_user_teams), reuse it directly — no need to search again.
          2. If you only have the name, call list_user_teams first to get the GUID.
          3. Pass only the UUID here (e.g. '7932e3f3-67f1-4ede-809e-dc943c43cab5').
        """
        p = GetTeamSettingsParams.model_validate({"team_id": team_id, "response_format": response_format})
        try:
            result = await teams_service.get_team_settings(p.team_id)
        except Exception as exc:
            result = graph_error_response(exc, context=f"settings for team '{p.team_id}'")
        return render_response(result, p.response_format)

    @mcp.tool(name="get_channel_settings", annotations={**_ANNOTATIONS, "title": "Get Channel Settings"})
    @audited
    async def get_channel_settings(
        team_id: str,
        channel_id: str,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> Any:
        """Return settings for a specific channel within a Team.

        PARAMETERS:
          - team_id: group GUID. Obtain via list_user_teams. NEVER pass a display name.
          - channel_id: channel ID (e.g. '19:abc123@thread.tacv2'). Obtain via list_team_channels.
        """
        p = GetChannelSettingsParams.model_validate({"team_id": team_id, "channel_id": channel_id, "response_format": response_format})
        try:
            result = await teams_service.get_channel_settings(p.team_id, p.channel_id)
        except Exception as exc:
            result = graph_error_response(exc, context=f"channel '{p.channel_id}' in team '{p.team_id}'")
        return render_response(result, p.response_format)

    @mcp.tool(name="check_private_shared_channels", annotations={**_ANNOTATIONS, "title": "Check Private/Shared Channels"})
    @audited
    async def check_private_shared_channels(
        team_id: str,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> Any:
        """Identify private and shared channels in a specific Team.

        PARAMETERS:
          - team_id: group GUID. Obtain via list_user_teams. NEVER pass a display name.
        """
        p = CheckPrivateSharedChannelsParams.model_validate({"team_id": team_id, "response_format": response_format})
        try:
            result = await teams_service.check_private_shared_channels(p.team_id)
        except Exception as exc:
            result = graph_error_response(exc, context=f"channels in team '{p.team_id}'")
        return render_response(result, p.response_format)

    @mcp.tool(name="detect_orphaned_team", annotations={**_ANNOTATIONS, "title": "Detect Orphaned Team"})
    @audited
    async def detect_orphaned_team(
        team_id: str,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> Any:
        """Check if a specific Team has zero members (orphaned).

        NOTE: This tool checks ONE team at a time.
        For a tenant-wide view of ALL teams without members, use list_teams_without_members
        or get_tenant_teams_stats instead.
        PARAMETERS:
          - team_id: group GUID. Obtain via list_user_teams. NEVER pass a display name.
        """
        p = DetectOrphanedTeamParams.model_validate({"team_id": team_id, "response_format": response_format})
        try:
            result = await teams_service.detect_orphaned_team(p.team_id)
        except Exception as exc:
            result = graph_error_response(exc, context=f"team '{p.team_id}'")
        return render_response(result, p.response_format)

    @mcp.tool(name="detect_team_without_owner", annotations={**_ANNOTATIONS, "title": "Detect Team Without Owner"})
    @audited
    async def detect_team_without_owner(
        team_id: str,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> Any:
        """Check if a specific Team has no owners assigned.

        NOTE: This tool checks ONE team at a time.
        For a tenant-wide list of ALL orphaned teams (no owners), use list_orphaned_teams
        or get_tenant_teams_stats instead.
        PARAMETERS:
          - team_id: group GUID. Obtain via list_user_teams. NEVER pass a display name.
        """
        p = DetectTeamWithoutOwnerParams.model_validate({"team_id": team_id, "response_format": response_format})
        try:
            result = await teams_service.detect_team_without_owner(p.team_id)
        except Exception as exc:
            result = graph_error_response(exc, context=f"team '{p.team_id}'")
        return render_response(result, p.response_format)

    # ── tenant-wide analytics tools ───────────────────────────────────────────

    @mcp.tool(name="list_all_teams", annotations={**_ANNOTATIONS, "title": "List All Teams"})
    @audited
    async def list_all_teams(
        top: int = 20,
        skip: int = 0,
        privacy: str | None = None,
        include_counts: bool = True,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> Any:
        """List all Teams in the tenant with pagination and optional filters.

        USE as the entry point to browse the full inventory of groups.
        TYPICAL FLOW:
          - General overview:        list_all_teams(top=20)
          - Filter by privacy type:  list_all_teams(privacy='Private', top=20)
          - Without member counts:   list_all_teams(include_counts=False, top=50)
          - Next page:               list_all_teams(skip=20)
        PARAMETERS:
          - top: page size (default 20, max 100).
          - skip: records to skip for pagination (ignored when privacy filter is set).
          - privacy: 'Public' or 'Private'. Applied client-side (Graph API limitation —
                     $filter=visibility is not supported for groups). Fetches a larger
                     batch internally and filters locally.
          - include_counts: include memberCount and ownerCount per team. Default True.
                            Set False for faster browsing when counts are not needed.
        RETURNS: list of teams with id, name, visibility, createdDateTime, member and
                 owner counts (when include_counts=True).
        """
        p = ListAllTeamsParams.model_validate({
            "top": top, "skip": skip, "privacy": privacy,
            "include_counts": include_counts, "response_format": response_format,
        })
        try:
            result = await teams_service.list_all_teams(p.top, p.skip, p.privacy, p.include_counts)
        except Exception as exc:
            result = graph_error_response(exc, context="listing all teams")
        return render_response(result, p.response_format)

    @mcp.tool(name="get_tenant_teams_stats", annotations={**_ANNOTATIONS, "title": "Get Tenant Teams Stats"})
    @audited
    async def get_tenant_teams_stats(
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> Any:
        """Return consolidated statistics for all Teams in the tenant.

        USE when: the user wants a panoramic overview — total groups, breakdown by
        privacy type, and how many are orphaned (no owners).
        RETURNS:
          - total_teams: total Teams-enabled groups in the tenant.
          - by_visibility: public / private breakdown (full tenant scan, client-side).
          - health.orphaned_no_owners: groups with no owner assigned (exact count).
          - health.no_members: use list_teams_without_members for the actual list.
        PERFORMANCE: Runs 3 operations in parallel:
          1. Total count ($count query — fast).
          2. Orphaned count (owners/$count eq 0 — fast).
          3. Visibility scan (paginates all groups for public/private breakdown —
             may take a few seconds for large tenants).
        GRAPH API LIMITATION: $filter=visibility is not supported for groups.
        Visibility counts are obtained via a full paginated client-side scan.
        TYPICAL FLOW:
          1. get_tenant_teams_stats -> overview
          2. list_orphaned_teams    -> detail groups without owners
          3. list_teams_without_members -> detail groups without members
        """
        p = GetTenantTeamsStatsParams.model_validate({"response_format": response_format})
        try:
            result = await teams_service.get_tenant_teams_stats()
        except Exception as exc:
            result = graph_error_response(exc, context="tenant teams statistics")
        return render_response(result, p.response_format)

    @mcp.tool(name="list_orphaned_teams", annotations={**_ANNOTATIONS, "title": "List Orphaned Teams"})
    @audited
    async def list_orphaned_teams(
        top: int = 20,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> Any:
        """List all Teams in the tenant that have no owners (orphaned groups).

        USE when: the user asks 'which groups are orphaned?' or 'which have no owner?'
        For checking a single specific group, use detect_team_without_owner instead.
        PARAMETERS:
          - top: max groups to return (default 20, max 100).
        RETURNS: list of ownerless groups with member count + total count in the tenant.
        NOTE: Member count is always included in the response to help identify
        truly inactive groups (no owners AND no members).
        """
        p = ListOrphanedTeamsParams.model_validate({"top": top, "response_format": response_format})
        try:
            result = await teams_service.list_orphaned_teams(p.top)
        except Exception as exc:
            result = graph_error_response(exc, context="orphaned teams")
        return render_response(result, p.response_format)

    @mcp.tool(name="list_teams_without_members", annotations={**_ANNOTATIONS, "title": "List Teams Without Members"})
    @audited
    async def list_teams_without_members(
        top: int = 20,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> Any:
        """List Teams in the tenant that have no members (empty groups).

        USE when: the user asks 'which groups are empty?' or 'which have no members?'
        For checking a single specific group, use detect_orphaned_team instead.
        PARAMETERS:
          - top: max groups to SHOW in the list (default 20, max 100).
                 Does NOT affect scan coverage — the full tenant is always scanned.
        RETURNS: empty groups found + total count across full scan.
        GRAPH API LIMITATION: $filter=members/$count eq 0 is not supported for groups.
        This tool paginates through ALL teams (100 per page, up to 5000 teams),
        checking member counts in parallel (up to 20 concurrent checks).
        The total count shown reflects ALL empty teams found, not just the listed ones.
        PERFORMANCE: Scanning 4000+ teams takes approximately 40–80 seconds.
        """
        p = ListTeamsWithoutMembersParams.model_validate({"top": top, "response_format": response_format})
        try:
            result = await teams_service.list_teams_without_members(p.top)
        except Exception as exc:
            result = graph_error_response(exc, context="teams without members")
        return render_response(result, p.response_format)

    @mcp.tool(name="list_teams_by_member_count", annotations={**_ANNOTATIONS, "title": "List Teams by Member Count"})
    @audited
    async def list_teams_by_member_count(
        top: int = 10,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> Any:
        """List the largest Teams ranked by member count.

        USE when: the user asks 'which are the largest groups?' or 'most members?'
        PARAMETERS:
          - top: how many groups to return in the ranking (default 10, max 50).
        RETURNS: groups sorted by memberCount descending with member counts shown.
        PERFORMANCE: Scans ALL teams in the tenant (full paginated scan, up to 5000
        teams, 100 per page, 20 parallel member-count checks per batch).
        Scanning 4000+ teams takes approximately 40–80 seconds.
        NOTE: Previous sample-based approach (alphabetical batch) was inaccurate
        because the first alphabetical groups tend to be inactive/empty.
        """
        p = ListTeamsByMemberCountParams.model_validate({"top": top, "response_format": response_format})
        try:
            result = await teams_service.list_teams_by_member_count(p.top)
        except Exception as exc:
            result = graph_error_response(exc, context="teams by member count")
        return render_response(result, p.response_format)
