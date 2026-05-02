from __future__ import annotations
from typing import Any
from fastmcp import FastMCP
from mcp_msteams.logging_config import audited
from mcp_msteams.schemas.common import ResponseFormat
from mcp_msteams.services import messages_service
from mcp_msteams.utils.response import graph_error_response, render_response

_ANNOTATIONS = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}


def _register(mcp: FastMCP) -> None:
    @mcp.tool(name="get_recent_channel_messages", annotations={**_ANNOTATIONS, "title": "Get Recent Channel Messages"})
    @audited
    async def get_recent_channel_messages(team_id: str, channel_id: str, count: int = 20, response_format: ResponseFormat = ResponseFormat.MARKDOWN) -> Any:
        """Retrieve recent messages from a channel."""
        try:
            result = await messages_service.get_recent_channel_messages(team_id, channel_id, count)
        except Exception as exc:
            result = graph_error_response(exc, context=f"messages in channel '{channel_id}'")
        return render_response(result, response_format)

    @mcp.tool(name="search_channel_messages", annotations={**_ANNOTATIONS, "title": "Search Channel Messages"})
    @audited
    async def search_channel_messages(team_id: str, channel_id: str, query: str, response_format: ResponseFormat = ResponseFormat.MARKDOWN) -> Any:
        """Search messages in a channel by keyword (case-insensitive, local filter on most recent ~50 messages).
        Limitation: does not use Microsoft Search API — results limited to recent messages only."""
        try:
            result = await messages_service.search_channel_messages(team_id, channel_id, query)
        except Exception as exc:
            result = graph_error_response(exc, context=f"searching channel '{channel_id}'")
        return render_response(result, response_format)

    @mcp.tool(name="summarize_channel_activity", annotations={**_ANNOTATIONS, "title": "Summarize Channel Activity"})
    @audited
    async def summarize_channel_activity(team_id: str, channel_id: str, days: int = 7, response_format: ResponseFormat = ResponseFormat.MARKDOWN) -> Any:
        """Summarise message activity in a channel over N days."""
        try:
            result = await messages_service.summarize_channel_activity(team_id, channel_id, days)
        except Exception as exc:
            result = graph_error_response(exc, context=f"activity in channel '{channel_id}'")
        return render_response(result, response_format)
