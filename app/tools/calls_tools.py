from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from app.logging_config import audited
from app.schemas.calls import (
    DiagnoseCallQualityParams,
    GetCallQualitySummaryParams,
    ListFailedCallsParams,
    ListPoorQualityCallsParams,
)
from app.schemas.common import ResponseFormat
from app.services import calls_service
from app.utils.response import render_response, graph_error_response

_ANNOTATIONS = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}


def _register(mcp: FastMCP) -> None:
    @mcp.tool(name="get_call_quality_summary", annotations={**_ANNOTATIONS, "title": "Get Call Quality Summary"})
    @audited
    async def get_call_quality_summary(
        upn: str,
        days: int = 7,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> Any:
        """
        Summarise call statistics for a user over the past N days (total, failed, success rate).

        USE when: Admin reports "user has been having call problems" — get the big picture first.
        Note: Call Records API has up to 15 minutes latency for recent calls.

        FLOW: get_call_quality_summary → if failed calls found: list_failed_calls →
              pick a call_id → diagnose_call_quality for session-level detail.

        REQUIRES: upn — full email address.
        """
        p = GetCallQualitySummaryParams.model_validate({"upn": upn, "days": days, "response_format": response_format})
        try:
            result = await calls_service.get_call_quality_summary(p.upn, p.days)
        except Exception as exc:
            result = graph_error_response(exc, context=f"call records for '{p.upn}'")
        return render_response(result, p.response_format)

    @mcp.tool(name="diagnose_call_quality", annotations={**_ANNOTATIONS, "title": "Diagnose Call Quality"})
    @audited
    async def diagnose_call_quality(
        call_id: str,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> Any:
        """
        Diagnose a specific call using session and participant data from the Call Records API.

        USE when: You have a specific call_id (from list_failed_calls or list_poor_quality_calls)
        and need to understand what went wrong — codec, network, session breakdown.

        REQUIRES: call_id — get this from the 'id' field in results of list_failed_calls
        or list_poor_quality_calls.
        Note: Call Records API may have up to 15 minutes latency.
        """
        p = DiagnoseCallQualityParams.model_validate({"call_id": call_id, "response_format": response_format})
        try:
            result = await calls_service.diagnose_call_quality(p.call_id)
        except Exception as exc:
            result = graph_error_response(exc, context=f"call record '{p.call_id}'")
        return render_response(result, p.response_format)

    @mcp.tool(name="list_failed_calls", annotations={**_ANNOTATIONS, "title": "List Failed Calls"})
    @audited
    async def list_failed_calls(
        upn: str,
        days: int = 7,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> Any:
        """List calls that ended with a failure result for a user."""
        p = ListFailedCallsParams.model_validate({"upn": upn, "days": days, "response_format": response_format})
        try:
            result = await calls_service.list_failed_calls(p.upn, p.days)
        except Exception as exc:
            result = graph_error_response(exc, context=f"failed calls for '{p.upn}'")
        return render_response(result, p.response_format)

    @mcp.tool(name="list_poor_quality_calls", annotations={**_ANNOTATIONS, "title": "List Poor Quality Calls"})
    @audited
    async def list_poor_quality_calls(
        upn: str,
        days: int = 7,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> Any:
        """List calls with poor quality indicators. Use diagnose_call_quality for full session metrics."""
        p = ListPoorQualityCallsParams.model_validate({"upn": upn, "days": days, "response_format": response_format})
        try:
            result = await calls_service.list_poor_quality_calls(p.upn, p.days)
        except Exception as exc:
            result = graph_error_response(exc, context=f"call records for '{p.upn}'")
        return render_response(result, p.response_format)
