from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from app.logging_config import audited
from app.services import audit_service

_ANNOTATIONS = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": False}


def _register(mcp: FastMCP) -> None:
    @mcp.tool(name="execution_history", annotations={**_ANNOTATIONS, "title": "Execution History"})
    @audited
    async def execution_history(limit: int = 50) -> Any:
        """Return a log of the last N tool invocations (metadata only, no response content)."""
        entries = audit_service.get_history(limit=min(limit, 200))
        lines = [f"## Execution History (last {len(entries)} calls)"]
        lines.append("| Time | Tool | UPN hint | Elapsed ms | Status |")
        lines.append("|---|---|---|---|---|")
        for e in entries:
            lines.append(f"| {e['timestamp'][:19]} | {e['tool']} | {e['upn_hint']} | {e['elapsed_ms']} | {e['status']} |")
        return {"entries": entries, "markdown": "\n".join(lines)}

    @mcp.tool(name="who_did_what", annotations={**_ANNOTATIONS, "title": "Who Did What"})
    @audited
    async def who_did_what(upn_hint: str, limit: int = 20) -> Any:
        """Return audit entries filtered by UPN hint (domain-fragment match). Shows which tools were invoked for a user."""
        entries = audit_service.get_by_upn(upn_hint, limit=limit)
        lines = [f"## Activity for '{upn_hint}' ({len(entries)} entries)"]
        for e in entries:
            lines.append(f"- {e['timestamp'][:19]} | {e['tool']} | {e['status']} | {e['elapsed_ms']}ms")
        return {"upn_hint": upn_hint, "entries": entries, "markdown": "\n".join(lines)}

    @mcp.tool(name="support_case_summary", annotations={**_ANNOTATIONS, "title": "Support Case Summary"})
    @audited
    async def support_case_summary() -> Any:
        """Return aggregate statistics about tool usage in this session (total calls, error rate, tools used)."""
        summary = audit_service.get_summary()
        lines = ["## Support Session Summary"]
        lines.append(f"- **Total calls:** {summary.get('total_calls', 0)}")
        lines.append(f"- **Errors:** {summary.get('error_count', 0)}")
        lines.append(f"- **Success rate:** {summary.get('success_rate', 'N/A')}")
        lines.append(f"- **Avg elapsed:** {summary.get('avg_elapsed_ms', 0)}ms")
        tools = summary.get('tools_used', [])
        if tools:
            lines.append(f"- **Tools used:** {', '.join(tools)}")
        summary["markdown"] = "\n".join(lines)
        return summary
