from __future__ import annotations
from typing import Any
from fastmcp import FastMCP
from app.logging_config import audited
from app.schemas.common import ResponseFormat
from app.services import messages_service

_ANNOTATIONS = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}


def _register(mcp: FastMCP) -> None:
    @mcp.tool(name="get_recent_channel_messages", annotations={**_ANNOTATIONS, "title": "Get Recent Channel Messages"})
    @audited
    async def get_recent_channel_messages(team_id: str, channel_id: str, count: int = 20, response_format: ResponseFormat = ResponseFormat.MARKDOWN) -> Any:
        """[STUB] Retrieve recent messages from a channel. Requires ChannelMessage.Read.All."""
        return await messages_service.get_recent_channel_messages(team_id, channel_id, count)

    @mcp.tool(name="search_channel_messages", annotations={**_ANNOTATIONS, "title": "Search Channel Messages"})
    @audited
    async def search_channel_messages(team_id: str, channel_id: str, query: str, response_format: ResponseFormat = ResponseFormat.MARKDOWN) -> Any:
        """[STUB] Search messages in a channel. Requires Graph Search API + ChannelMessage.Read.All."""
        return await messages_service.search_channel_messages(team_id, channel_id, query)

    @mcp.tool(name="summarize_channel_activity", annotations={**_ANNOTATIONS, "title": "Summarize Channel Activity"})
    @audited
    async def summarize_channel_activity(team_id: str, channel_id: str, days: int = 7, response_format: ResponseFormat = ResponseFormat.MARKDOWN) -> Any:
        """[STUB] Summarise message activity in a channel over N days."""
        return await messages_service.summarize_channel_activity(team_id, channel_id, days)
