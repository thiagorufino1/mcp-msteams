from __future__ import annotations
from typing import Any
from fastmcp import FastMCP
from app.logging_config import audited
from app.schemas.common import ResponseFormat
from app.services import meetings_service

_ANNOTATIONS = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}


def _register(mcp: FastMCP) -> None:
    @mcp.tool(name="get_recent_meetings", annotations={**_ANNOTATIONS, "title": "Get Recent Meetings"})
    @audited
    async def get_recent_meetings(upn: str, days: int = 7, response_format: ResponseFormat = ResponseFormat.MARKDOWN) -> Any:
        """[STUB] List recent online meetings for a user. Requires OnlineMeetings.Read.All."""
        return await meetings_service.get_recent_meetings(upn, days)

    @mcp.tool(name="diagnose_meeting_issues", annotations={**_ANNOTATIONS, "title": "Diagnose Meeting Issues"})
    @audited
    async def diagnose_meeting_issues(meeting_id: str, response_format: ResponseFormat = ResponseFormat.MARKDOWN) -> Any:
        """[STUB] Diagnose a specific meeting including attendance and quality data."""
        return await meetings_service.diagnose_meeting_issues(meeting_id)
