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
from app.utils.response import render_response, graph_error_response

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
        """Return detailed Azure AD profile for a user."""
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
        """Return real-time Teams presence status for a user (Available, Busy, Away, etc.)."""
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
        """Return Teams policies assigned to a user (meeting, calling, messaging, etc.)."""
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
        """List all Microsoft Teams the user is a member of."""
        p = ListUserTeamsParams.model_validate({"upn": upn, "response_format": response_format})
        try:
            result = await users_service.list_user_teams(p.upn)
        except Exception as exc:
            result = graph_error_response(exc, context=f"teams for '{p.upn}'")
        return render_response(result, p.response_format)
