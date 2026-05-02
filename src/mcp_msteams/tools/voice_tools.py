from __future__ import annotations
from typing import Any
from fastmcp import FastMCP
from mcp_msteams.logging_config import audited
from mcp_msteams.schemas.common import ResponseFormat
from mcp_msteams.services import voice_service
from mcp_msteams.utils.response import graph_error_response, render_response

_ANNOTATIONS = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}


def _register(mcp: FastMCP) -> None:
    @mcp.tool(name="get_voice_configuration", annotations={**_ANNOTATIONS, "title": "Get Voice Configuration"})
    @audited
    async def get_voice_configuration(upn: str, response_format: ResponseFormat = ResponseFormat.MARKDOWN) -> Any:
        """Return voice/Teams Phone policy configuration for a user.
        Note: based on assigned policy names — does not validate phone number provisioning or licensing."""
        try:
            result = await voice_service.get_voice_configuration(upn)
        except Exception as exc:
            result = graph_error_response(exc, context=f"voice configuration for '{upn}'")
        return render_response(result, response_format)

    @mcp.tool(name="validate_voice_routing", annotations={**_ANNOTATIONS, "title": "Validate Voice Routing"})
    @audited
    async def validate_voice_routing(upn: str, response_format: ResponseFormat = ResponseFormat.MARKDOWN) -> Any:
        """Validate voice routing policy assignment for a user.
        Note: checks policy presence by name pattern — does not validate actual call routing rules or PSTN connectivity."""
        try:
            result = await voice_service.validate_voice_routing(upn)
        except Exception as exc:
            result = graph_error_response(exc, context=f"voice routing for '{upn}'")
        return render_response(result, response_format)

    @mcp.tool(name="detect_voice_misconfiguration", annotations={**_ANNOTATIONS, "title": "Detect Voice Misconfiguration"})
    @audited
    async def detect_voice_misconfiguration(upn: str, response_format: ResponseFormat = ResponseFormat.MARKDOWN) -> Any:
        """Detect common Teams Phone misconfigurations for a user."""
        try:
            result = await voice_service.detect_voice_misconfiguration(upn)
        except Exception as exc:
            result = graph_error_response(exc, context=f"voice misconfiguration for '{upn}'")
        return render_response(result, response_format)
