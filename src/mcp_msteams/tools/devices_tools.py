from __future__ import annotations
from typing import Any
from fastmcp import FastMCP
from mcp_msteams.logging_config import audited
from mcp_msteams.schemas.common import ResponseFormat
from mcp_msteams.services import devices_service
from mcp_msteams.utils.response import graph_error_response, render_response

_ANNOTATIONS = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}


def _register(mcp: FastMCP) -> None:
    @mcp.tool(name="get_user_devices", annotations={**_ANNOTATIONS, "title": "Get User Devices"})
    @audited
    async def get_user_devices(upn: str, response_format: ResponseFormat = ResponseFormat.MARKDOWN) -> Any:
        """List devices registered for a user."""
        try:
            result = await devices_service.get_user_devices(upn)
        except Exception as exc:
            result = graph_error_response(exc, context=f"devices for '{upn}'")
        return render_response(result, response_format)

    @mcp.tool(name="detect_device_problems", annotations={**_ANNOTATIONS, "title": "Detect Device Problems"})
    @audited
    async def detect_device_problems(upn: str, response_format: ResponseFormat = ResponseFormat.MARKDOWN) -> Any:
        """Detect compliance or sync issues on a user's devices."""
        try:
            result = await devices_service.detect_device_problems(upn)
        except Exception as exc:
            result = graph_error_response(exc, context=f"device problems for '{upn}'")
        return render_response(result, response_format)
