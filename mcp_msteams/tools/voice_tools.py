from __future__ import annotations
from typing import Any
from fastmcp import FastMCP
from mcp_msteams.logging_config import audited
from mcp_msteams.schemas.common import ResponseFormat
from mcp_msteams.services import voice_service

_ANNOTATIONS = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}


def _register(mcp: FastMCP) -> None:
    @mcp.tool(name="get_voice_configuration", annotations={**_ANNOTATIONS, "title": "Get Voice Configuration"})
    @audited
    async def get_voice_configuration(upn: str, response_format: ResponseFormat = ResponseFormat.MARKDOWN) -> Any:
        """[STUB] Return voice/Teams Phone configuration for a user."""
        return await voice_service.get_voice_configuration(upn)

    @mcp.tool(name="validate_voice_routing", annotations={**_ANNOTATIONS, "title": "Validate Voice Routing"})
    @audited
    async def validate_voice_routing(upn: str, response_format: ResponseFormat = ResponseFormat.MARKDOWN) -> Any:
        """[STUB] Validate voice routing policy configuration for a user."""
        return await voice_service.validate_voice_routing(upn)

    @mcp.tool(name="detect_voice_misconfiguration", annotations={**_ANNOTATIONS, "title": "Detect Voice Misconfiguration"})
    @audited
    async def detect_voice_misconfiguration(upn: str, response_format: ResponseFormat = ResponseFormat.MARKDOWN) -> Any:
        """[STUB] Detect common Teams Phone misconfigurations for a user."""
        return await voice_service.detect_voice_misconfiguration(upn)
