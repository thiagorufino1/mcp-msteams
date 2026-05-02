from __future__ import annotations

from typing import Any

from mcp_msteams.graph import endpoints
from mcp_msteams.graph.client import graph_get_all
from mcp_msteams.security.permissions import SCOPES


async def check_known_teams_incidents() -> dict[str, Any]:
    issues = await graph_get_all(
        endpoints.service_announcement_issues(),
        scopes=SCOPES["service_health"],
        max_pages=5,
    )
    teams_issues = [
        issue for issue in issues
        if "teams" in str(issue.get("service", "")).lower()
        or "teams" in str(issue.get("title", "")).lower()
    ]
    lines = [f"## Known Teams Incidents ({len(teams_issues)})"]
    for issue in teams_issues[:20]:
        lines.append(
            f"- **{issue.get('title', issue.get('id', '?'))}** | "
            f"status: {issue.get('status', '?')} | classification: {issue.get('classification', '?')}"
        )
    if len(teams_issues) > 20:
        lines.append(f"- ...and {len(teams_issues) - 20} more")
    return {
        "issues": teams_issues,
        "count": len(teams_issues),
        "markdown": "\n".join(lines),
    }
