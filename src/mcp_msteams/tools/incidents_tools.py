from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from mcp_msteams.logging_config import audited
from mcp_msteams.services import incidents_service
from mcp_msteams.utils.response import graph_error_response

_ANNOTATIONS = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}


def _register(mcp: FastMCP) -> None:
    @mcp.tool(name="check_known_teams_incidents", annotations={**_ANNOTATIONS, "title": "Check Known Teams Incidents"})
    @audited
    async def check_known_teams_incidents() -> Any:
        """List only open Microsoft Teams service health items, split between incidents and advisories, with issue IDs.

        DISPLAY RULES:
        - Always show the full markdown returned by the tool.
        - Keep the table format with columns `ID`, `Título`, and `Resumo das atividades`.
        - The `Resumo das atividades` column must be derived from `get_teams_incident_detail`-style history for each open item,
          not just repeat the title or impact.
        - Do not truncate the `Resumo das atividades` text with `...` or shorten it unnecessarily.
          Keep the full relevant activity text for each row.
        - For each open item, summarize the activity/history with the most relevant facts: root cause, workaround/mitigation,
          deployment or rollback progress, ETA/next update, and current state.
        - Do not rewrite the result as a generic bullet list when the user asked about service integrity/status.
        - If user asks about a specific item or says only an issue ID, ALWAYS call `get_teams_incident_detail`.
        - Do not answer an issue ID request from memory, prior chat context, or a previous tool result.
          Re-fetch the current detail every time the user asks for an issue ID, even if that ID already appeared earlier.
        - If there are zero incidents but open advisories, say that clearly instead of saying the service is fully normal.
        - If user asks for "integridade do Teams", "status do Teams", "saúde do Teams", or similar overview,
          the default response should preserve the table, not convert it to bullets.
        - If the user asked in Portuguese, translate the full table content to pt-BR.
        - If user asks for a summary/resumo of current activity or what changed, use this tool first to get the open IDs,
          then call `get_teams_incident_detail` for the relevant items and summarize the latest meaningful updates.
        - For these summaries, do not rely only on title/impact. Inspect the updates/history from
          `get_teams_incident_detail` and highlight concrete changes such as cause identified, code change, mitigation,
          rollback, fix progress, ETA, or confirmation that there was no material change.
        """
        try:
            result = await incidents_service.check_known_teams_incidents()
        except Exception as exc:
            result = graph_error_response(exc, context="Teams service incidents")
        return result.get("markdown", result)

    @mcp.tool(name="get_teams_incident_detail", annotations={**_ANNOTATIONS, "title": "Get Teams Incident Detail"})
    @audited
    async def get_teams_incident_detail(issue_id: str) -> Any:
        """Get structured detail for one Microsoft Teams service health issue by issue_id.

        DISPLAY RULES:
        - If the user message is only an issue ID like `TM1290947`, ALWAYS call this tool immediately.
        - Never answer from memory, previous chat text, or previously cached conversational context.
          Use the tool result as the source of truth every time.
        - If user asks for updates/history, show ALL updates returned by the tool. Do not omit any update.
        - Do not truncate update text. If the content is long, continue in multiple messages/parts instead of shortening.
        - In each update entry, show only the useful update message content. Avoid repeating the same title/user-impact
          boilerplate in every item when it adds no new information.
        - If root cause is repeated across updates, show it once in a dedicated `Root Cause` section instead of
          repeating it inside every update entry.
        - If user asks in Portuguese, translate the update text completely to Portuguese while preserving technical meaning.
        - If user asks to summarize, preserve the important new fact from EACH update.
        - Never collapse updates into generic phrases like "follow-up", "acompanhamento", or "sem mudança"
          if the update contains new diagnostic or remediation information.
        - Highlight explicitly, in chronological order: likely cause, investigation findings, code/config changes,
          mitigation steps, fix progress, scope changes, ETA, and next actions.
        - If an update says something like "identified a recent code change as the likely cause", include that exact
          meaning in the summary. Do not omit it.
        - Preferred summary shape: `date -> what changed -> impact/next step`.
        """
        try:
            result = await incidents_service.get_teams_incident_detail(issue_id)
        except Exception as exc:
            result = graph_error_response(exc, context=f"Teams service issue '{issue_id}'")
        return result.get("markdown", result)
