from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from mcp_msteams.logging_config import audited
from mcp_msteams.schemas.calls import (
    DiagnoseCallQualityParams,
    GetCallQualitySummaryParams,
    ListFailedCallsParams,
)
from mcp_msteams.schemas.common import ResponseFormat
from mcp_msteams.services import calls_service
from mcp_msteams.utils.response import render_response, graph_error_response

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
        upn: str,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> Any:
        """
        Diagnose call quality for a participant. upn is REQUIRED — no default.

        upn: UPN (email) of the person to diagnose (e.g. "dtottene@cielo.com.br").
             - Pass "all" ONLY if user explicitly said "toda a chamada", "todos", or "geral".
             - DO NOT default to "all". "all" is NOT the default.

        FLOW — follow exactly:
        1. User says "diag da call X":
           → Ask ONCE: "Para qual participante? (nome ou e-mail — ou 'toda a chamada' para todos)"
        2. User responds with a name (e.g. "thiagoru", "thiago rufino", "danny"):
           → Call search_user to resolve the UPN.
           → IMMEDIATELY call diagnose_call_quality with the resolved UPN.
           → Do NOT ask for confirmation. Do NOT say "encontrei, se quiser faço...". Just do it.
        3. User responds with a full email → call diagnose_call_quality directly.
        4. User says "toda a chamada" → call with upn="all".

        NEVER add extra confirmation steps between resolving UPN and calling the diagnosis.

        DISPLAY: copy the FULL markdown result as-is. Do not summarize or rewrite.
        After the result, you may add at most 2 sentences of observation.
        """
        p = DiagnoseCallQualityParams.model_validate({"call_id": call_id, "response_format": response_format})
        resolved_upn = None if upn.strip().lower() == "all" else upn.strip()
        try:
            result = await calls_service.diagnose_call_quality(p.call_id, upn=resolved_upn)
        except Exception as exc:
            context = f"usuário '{resolved_upn}'" if resolved_upn else f"call record '{p.call_id}'"
            result = graph_error_response(exc, context=context)
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

