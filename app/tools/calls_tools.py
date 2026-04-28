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
from app.utils.response import render_response

_ANNOTATIONS = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}


def _register(mcp: FastMCP) -> None:
    @mcp.tool(name="get_call_quality_summary", annotations={**_ANNOTATIONS, "title": "Get Call Quality Summary"})
    @audited
    async def get_call_quality_summary(
        upn: str,
        days: int = 7,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> Any:
        """Summarise call quality metrics for a user over the past N days. Note: up to 15min data lag."""
        p = GetCallQualitySummaryParams.model_validate({"upn": upn, "days": days, "response_format": response_format})
        result = await calls_service.get_call_quality_summary(p.upn, p.days)
        return render_response(result, p.response_format)

    @mcp.tool(name="diagnose_call_quality", annotations={**_ANNOTATIONS, "title": "Diagnose Call Quality"})
    @audited
    async def diagnose_call_quality(
        call_id: str,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> Any:
        """Diagnose a specific call using session-level metrics from the Call Records API."""
        p = DiagnoseCallQualityParams.model_validate({"call_id": call_id, "response_format": response_format})
        result = await calls_service.diagnose_call_quality(p.call_id)
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
        result = await calls_service.list_failed_calls(p.upn, p.days)
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
        result = await calls_service.list_poor_quality_calls(p.upn, p.days)
        return render_response(result, p.response_format)
