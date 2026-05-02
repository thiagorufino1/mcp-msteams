from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from mcp_msteams.logging_config import audited
from mcp_msteams.schemas.common import ResponseFormat
from mcp_msteams.schemas.policies import CompareUserPoliciesParams, DetectPolicyConflictsParams
from mcp_msteams.services import policies_service
from mcp_msteams.utils.response import render_response, graph_error_response

_ANNOTATIONS = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}


def _register(mcp: FastMCP) -> None:
    @mcp.tool(name="compare_user_policies", annotations={**_ANNOTATIONS, "title": "Compare User Policies"})
    @audited
    async def compare_user_policies(
        upn1: str,
        upn2: str,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> Any:
        """Compare Teams policy assignments between two users — useful for troubleshooting policy discrepancies."""
        p = CompareUserPoliciesParams.model_validate({"upn1": upn1, "upn2": upn2, "response_format": response_format})
        try:
            result = await policies_service.compare_user_policies(p.upn1, p.upn2)
        except Exception as exc:
            result = graph_error_response(exc, context=f"policies for '{p.upn1}' and '{p.upn2}'")
        return render_response(result, p.response_format)

    @mcp.tool(name="detect_policy_conflicts", annotations={**_ANNOTATIONS, "title": "Detect Policy Conflicts"})
    @audited
    async def detect_policy_conflicts(
        upn: str,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> Any:
        """Detect known conflicting Teams policy combinations for a user."""
        p = DetectPolicyConflictsParams.model_validate({"upn": upn, "response_format": response_format})
        try:
            result = await policies_service.detect_policy_conflicts(p.upn)
        except Exception as exc:
            result = graph_error_response(exc, context=f"policies for '{p.upn}'")
        return render_response(result, p.response_format)
