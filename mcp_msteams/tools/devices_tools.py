from __future__ import annotations
from typing import Any
from fastmcp import FastMCP
from mcp_msteams.logging_config import audited
from mcp_msteams.schemas.common import ResponseFormat
from mcp_msteams.services import devices_service

_ANNOTATIONS = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}


def _register(mcp: FastMCP) -> None:
    @mcp.tool(name="get_user_devices", annotations={**_ANNOTATIONS, "title": "Get User Devices"})
    @audited
    async def get_user_devices(upn: str, response_format: ResponseFormat = ResponseFormat.MARKDOWN) -> Any:
        """[STUB] List devices registered for a user. Requires Directory.Read.All."""
        return await devices_service.get_user_devices(upn)

    @mcp.tool(name="detect_device_problems", annotations={**_ANNOTATIONS, "title": "Detect Device Problems"})
    @audited
    async def detect_device_problems(upn: str, response_format: ResponseFormat = ResponseFormat.MARKDOWN) -> Any:
        """[STUB] Detect compliance or sync issues on a user's devices."""
        return await devices_service.detect_device_problems(upn)
