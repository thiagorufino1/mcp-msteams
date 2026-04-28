from __future__ import annotations

from typing import Any

from app.schemas.common import ResponseFormat


def render_response(result: dict[str, Any], fmt: ResponseFormat) -> Any:
    if fmt == ResponseFormat.MARKDOWN:
        return result.get("markdown") or _auto_markdown(result)
    return result


def _auto_markdown(result: dict[str, Any]) -> str:
    lines: list[str] = []
    for key, value in result.items():
        if key == "markdown":
            continue
        if isinstance(value, dict):
            lines.append(f"**{key}:**")
            for k, v in value.items():
                lines.append(f"  - {k}: {v}")
        elif isinstance(value, list):
            lines.append(f"**{key}:** {len(value)} items")
        else:
            lines.append(f"**{key}:** {value}")
    return "\n".join(lines)


def build_markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    header_row = " | ".join(headers)
    separator = " | ".join(["---"] * len(headers))
    data_rows = [" | ".join(str(cell) for cell in row) for row in rows]
    return "\n".join([header_row, separator, *data_rows])


def not_implemented_response(tool_name: str, todo: str) -> dict[str, Any]:
    return {
        "status": "not_implemented",
        "tool": tool_name,
        "todo": todo,
        "markdown": (
            f"**{tool_name}** is not yet implemented in this MCP server. "
            f"This feature cannot be used to answer the question at this time. "
            f"Direct the admin to the Microsoft Teams admin center "
            f"(admin.teams.microsoft.com) for now."
        ),
    }


from app.graph.errors import NotFoundError, ThrottlingError, AuthError, GraphValidationError  # noqa: E402


def graph_error_response(exc: Exception, context: str = "") -> dict[str, Any]:
    """Convert a Graph API exception into a structured, LLM-actionable response."""
    if isinstance(exc, NotFoundError):
        return {
            "error": "not_found",
            "message": f"Resource not found{': ' + context if context else ''}.",
            "suggested_action": "Verify the ID or UPN with the admin. Use search_user or list_user_teams to resolve identifiers.",
            "markdown": f"**Not found:** {context or 'The requested resource'} does not exist in Microsoft 365. Verify the identifier.",
        }
    if isinstance(exc, ThrottlingError):
        return {
            "error": "throttled",
            "message": str(exc),
            "suggested_action": "Wait 15–30 seconds and retry the same tool call.",
            "markdown": f"**Graph API throttled.** {exc} — Wait 15–30 seconds and retry.",
        }
    if isinstance(exc, AuthError):
        return {
            "error": "permission_denied",
            "message": str(exc),
            "suggested_action": "Check that the Azure App Registration has the required Graph permissions consented.",
            "markdown": "**Permission denied.** The app registration may be missing a required Graph permission. Check Entra ID app registration.",
        }
    if isinstance(exc, GraphValidationError):
        return {
            "error": "invalid_input",
            "message": str(exc),
            "suggested_action": "Check the format of the input parameters (UPN must be email format, IDs must be GUIDs).",
            "markdown": f"**Invalid input:** {exc}. Verify parameter formats.",
        }
    return {
        "error": "graph_error",
        "message": str(exc),
        "suggested_action": "Retry the request. If the error persists, check Graph API status at status.office.com.",
        "markdown": f"**Graph API error:** {exc}. Retry or check service status.",
    }
