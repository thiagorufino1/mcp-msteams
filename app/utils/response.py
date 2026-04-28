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
