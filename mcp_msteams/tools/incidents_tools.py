from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from mcp_msteams.logging_config import audited
from mcp_msteams.services import incidents_service

_ANNOTATIONS = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}


def _register(mcp: FastMCP) -> None:
    @mcp.tool(name="check_known_teams_incidents", annotations={**_ANNOTATIONS, "title": "Check Known Teams Incidents"})
    @audited
    async def check_known_teams_incidents() -> Any:
        """[STUB] Check for known Microsoft Teams service incidents and health advisories. Requires ServiceHealth.Read.All."""
        return await incidents_service.check_known_teams_incidents()
