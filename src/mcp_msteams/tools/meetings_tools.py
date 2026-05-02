from __future__ import annotations
from typing import Any
from fastmcp import FastMCP
from mcp_msteams.logging_config import audited
from mcp_msteams.schemas.common import ResponseFormat
from mcp_msteams.services import meetings_service
from mcp_msteams.utils.response import graph_error_response, render_response

_ANNOTATIONS = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}


def _register(mcp: FastMCP) -> None:
    @mcp.tool(name="get_recent_meetings", annotations={**_ANNOTATIONS, "title": "Get Recent Meetings"})
    @audited
    async def get_recent_meetings(upn: str, days: int = 7, response_format: ResponseFormat = ResponseFormat.MARKDOWN) -> Any:
        """List recent calls and meetings for a user — both groupCall (meetings/conferences) and peerToPeer (1:1 calls).

        USE when: user asks to list, show, or count meetings, calls, or interactions for a user.
        DISPLAY: always show the full markdown table — never summarize or paraphrase it.
        The table includes a "Tipo" column: "Reunião" = groupCall, "Chamada 1:1" = peerToPeer.
        Always mention the breakdown (e.g. "13 total: 10 reuniões, 3 chamadas 1:1") in your response.
        DAYS: use 7 (default) unless user explicitly says "last 30 days", "last month", etc.
        FORMAT: never use response_format=json — markdown already has the full table.

        QUALITY STATUS RULE:
        When user asks for quality/status of multiple calls, ALWAYS run diagnose_call_quality
        for each call_id individually (in parallel) to get real CQD telemetry data.
        Never assume quality without running the actual diagnosis. Build a summary table from the real results.
        """
        try:
            result = await meetings_service.get_recent_meetings(upn, days)
        except Exception as exc:
            result = graph_error_response(exc, context=f"meetings for '{upn}'")
        return render_response(result, response_format)

    @mcp.tool(name="get_meeting_participants", annotations={**_ANNOTATIONS, "title": "Get Meeting Participants"})
    @audited
    async def get_meeting_participants(call_id: str, response_format: ResponseFormat = ResponseFormat.MARKDOWN) -> Any:
        """List all participants of a specific meeting/call by call_id.

        Use this when the user asks who attended a meeting, who was in a call, or wants participant names.
        call_id comes from get_recent_meetings or diagnose_meeting_issues output.

        DISPLAY RULES — MANDATORY:
        - Copy and paste the FULL markdown table to the user. Do NOT summarize or list only some participants.
        - Never use response_format=json — markdown already contains all participant details.
        """
        try:
            result = await meetings_service.get_meeting_participants(call_id)
        except Exception as exc:
            result = graph_error_response(exc, context=f"participants for call '{call_id}'")
        return render_response(result, response_format)
