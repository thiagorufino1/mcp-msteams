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
from app.utils.response import render_response, graph_error_response

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
        """List all members of a Team."""
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
        """Return the owners of a Team."""
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
        """Return configuration and settings for a Team."""
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
        """Return settings for a specific channel within a Team."""
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
        """Identify private and shared channels in a Team."""
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
        """Check if a Team has zero members (orphaned)."""
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
        """Check if a Team has no owners assigned."""
        p = DetectTeamWithoutOwnerParams.model_validate({"team_id": team_id, "response_format": response_format})
        try:
            result = await teams_service.detect_team_without_owner(p.team_id)
        except Exception as exc:
            result = graph_error_response(exc, context=f"team '{p.team_id}'")
        return render_response(result, p.response_format)
