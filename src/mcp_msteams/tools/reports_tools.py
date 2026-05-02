from __future__ import annotations
from typing import Any
from fastmcp import FastMCP
from mcp_msteams.logging_config import audited
from mcp_msteams.schemas.common import ResponseFormat
from mcp_msteams.services import reports_service
from mcp_msteams.utils.response import graph_error_response, render_response

_ANNOTATIONS = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}


def _register(mcp: FastMCP) -> None:
    @mcp.tool(name="get_user_activity_report", annotations={**_ANNOTATIONS, "title": "Get AV Breakdown Report"})
    @audited
    async def get_user_activity_report(upn: str, days: int = 7, response_format: ResponseFormat = ResponseFormat.MARKDOWN) -> Any:
        """Audio/video/screen share duration breakdown from the Teams Reports API.

        DO NOT use for: weekly summary, call counts, meeting counts, total duration.
        For weekly summary / resumo semanal → use get_recent_meetings (correct counts + total duration).

        USE ONLY when: user explicitly asks for audio duration vs video duration vs screen share duration breakdown,
        or needs 30/90/180-day activity data.

        Warning: counts from this tool (meetings/calls) differ from callRecords API and may not match the portal.
        days: 7, 30, 90, or 180 (default: 7).
        upn must be a valid email. If user provides a name, call search_user first.
        """
        try:
            result = await reports_service.get_user_activity_report(upn, days)
        except Exception as exc:
            result = graph_error_response(exc, context=f"activity report for '{upn}'")
        return render_response(result, response_format)
