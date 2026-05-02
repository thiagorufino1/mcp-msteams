from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from mcp_msteams.logging_config import audited
from mcp_msteams.schemas.common import ResponseFormat
from mcp_msteams.schemas.users import (
    GetUserAssignedPoliciesParams,
    GetUserOverviewParams,
    GetUserPresenceParams,
    GetUserProfileParams,
    ListUserTeamsParams,
    SearchUserParams,
)
from mcp_msteams.services import users_service
from mcp_msteams.utils.response import render_response, graph_error_response

_ANNOTATIONS = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}


def _register(mcp: FastMCP) -> None:
    @mcp.tool(name="get_user_overview", annotations={**_ANNOTATIONS, "title": "Get User Overview"})
    @audited
    async def get_user_overview(
        upn: str,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> Any:
        """
        Get a combined snapshot of a user's profile, presence, and Teams membership.

        USE when: Starting any user-focused support session. This is the recommended FIRST
        call — it combines profile, presence, and joined Teams in a single round-trip.

        DON'T USE when: You only need one sub-piece (e.g., presence alone). Use the
        dedicated tool to avoid redundant Graph calls.

        FLOW: get_user_overview → if policies needed: get_user_assigned_policies →
              if teams details needed: list_team_channels / list_team_members.

        REQUIRES: upn — the user's full email (user@domain.com). Use search_user first
        if you only have a display name.
        """
        p = GetUserOverviewParams.model_validate({"upn": upn, "response_format": response_format})
        try:
            result = await users_service.get_user_overview(p.upn)
        except Exception as exc:
            result = graph_error_response(exc, context=f"user '{p.upn}'")
        return render_response(result, p.response_format)

    @mcp.tool(name="get_user_profile", annotations={**_ANNOTATIONS, "title": "Get User Profile"})
    @audited
    async def get_user_profile(
        upn: str,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> Any:
        """
        Return the full Azure AD profile for a user (name, department, job title, office, phone).

        USE when: You need specific profile fields not returned by get_user_overview,
        or when the admin asks for HR-style information about a user.

        DON'T USE when: You already called get_user_overview — profile data is included there.

        REQUIRES: upn — full email address. Use search_user to resolve display names to UPNs.
        """
        p = GetUserProfileParams.model_validate({"upn": upn, "response_format": response_format})
        try:
            result = await users_service.get_user_profile(p.upn)
        except Exception as exc:
            result = graph_error_response(exc, context=f"user '{p.upn}'")
        return render_response(result, p.response_format)

    @mcp.tool(name="get_user_presence", annotations={**_ANNOTATIONS, "title": "Get User Presence"})
    @audited
    async def get_user_presence(
        upn: str,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> Any:
        """
        Return the current Teams presence status for a user (Available, Busy, Away, Offline, etc.).

        USE when: The admin asks "is Alice online?" or "what is Bob's Teams status?".
        Note: Presence data is cached for 30 seconds — very recent changes may not appear.

        REQUIRES: upn — full email address.
        PERMISSION: Presence.Read.All — not available on all tenant license tiers.
        """
        p = GetUserPresenceParams.model_validate({"upn": upn, "response_format": response_format})
        try:
            result = await users_service.get_user_presence(p.upn)
        except Exception as exc:
            result = graph_error_response(exc, context=f"presence for '{p.upn}'")
        return render_response(result, p.response_format)

    @mcp.tool(name="get_user_assigned_policies", annotations={**_ANNOTATIONS, "title": "Get User Assigned Policies"})
    @audited
    async def get_user_assigned_policies(
        upn: str,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> Any:
        """
        Return Teams policies assigned to a user (meeting policy, calling policy, messaging policy, etc.).

        USE when: Troubleshooting missing features — e.g., user can't record meetings,
        can't make external calls, or can't use certain Teams features.

        FLOW: get_user_assigned_policies → if two users have different behavior:
        compare_user_policies → detect_policy_conflicts.

        REQUIRES: upn — full email address.
        PERMISSION: TeamsUserConfiguration.Read.All.
        """
        p = GetUserAssignedPoliciesParams.model_validate({"upn": upn, "response_format": response_format})
        try:
            result = await users_service.get_user_assigned_policies(p.upn)
        except Exception as exc:
            result = graph_error_response(exc, context=f"policies for '{p.upn}'")
        return render_response(result, p.response_format)

    @mcp.tool(name="list_user_teams", annotations={**_ANNOTATIONS, "title": "List User Teams"})
    @audited
    async def list_user_teams(
        upn: str,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> Any:
        """
        List all Microsoft Teams the user is a member of, including team IDs.

        USE when: You need a team_id (GUID) for subsequent tools like list_team_channels
        or list_team_members. Team display names alone are not enough — you need the GUID.

        FLOW: list_user_teams → copy team 'id' field → use in list_team_channels,
        list_team_members, get_team_settings, etc.

        REQUIRES: upn — full email address.
        """
        p = ListUserTeamsParams.model_validate({"upn": upn, "response_format": response_format})
        try:
            result = await users_service.list_user_teams(p.upn)
        except Exception as exc:
            result = graph_error_response(exc, context=f"teams for '{p.upn}'")
        return render_response(result, p.response_format)

    @mcp.tool(name="search_user", annotations={**_ANNOTATIONS, "title": "Search User"})
    @audited
    async def search_user(
        query: str,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> Any:
        """
        Search for Azure AD users by display name or email fragment. Returns UPNs needed for other tools.

        USE THIS FIRST when: The admin provides a name or partial email instead of a full UPN.
        All other user tools require a full UPN — use this to resolve it.

        FLOW: search_user('Alice Smith') → copy userPrincipalName → pass to get_user_overview,
              get_user_presence, get_user_assigned_policies, etc.

        Returns up to 10 matching users with displayName, UPN, job title, and department.
        """
        p = SearchUserParams.model_validate({"query": query, "response_format": response_format})
        try:
            result = await users_service.search_user(p.query)
        except Exception as exc:
            result = graph_error_response(exc, context=f"searching for '{query}'")
        return render_response(result, p.response_format)
