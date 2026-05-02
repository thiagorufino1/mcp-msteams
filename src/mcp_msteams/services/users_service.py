from __future__ import annotations

import asyncio
from typing import Any

from mcp_msteams.config import settings
from mcp_msteams.graph import endpoints
from mcp_msteams.graph.errors import NotFoundError
from mcp_msteams.graph.client import graph_get, graph_get_all
from mcp_msteams.security.permissions import SCOPES


async def get_user_profile(upn: str) -> dict[str, Any]:
    return await graph_get(
        endpoints.user(upn),
        scopes=SCOPES["user_read"],
        cache_key=f"user:{upn}",
        ttl=settings.cache_ttl_user,
    )


async def get_user_presence(upn: str) -> dict[str, Any]:
    profile = await get_user_profile(upn)
    user_id = profile.get("id", upn)
    return await graph_get(
        endpoints.user_presence(user_id),
        scopes=SCOPES["presence_read"],
        cache_key=f"presence:{user_id}",
        ttl=settings.cache_ttl_presence,
    )


async def list_user_teams(upn: str) -> dict[str, Any]:
    teams = await graph_get_all(
        endpoints.user_joined_teams(upn),
        scopes=SCOPES["team_read"],
    )
    lines = [f"## Teams for {upn} ({len(teams)})"]
    for t in teams:
        lines.append(f"- **{t.get('displayName', '?')}** (`{t.get('id', '?')}`)")
    return {"value": teams, "count": len(teams), "markdown": "\n".join(lines)}


async def get_user_assigned_policies(upn: str) -> dict[str, Any]:
    data = await graph_get(
        endpoints.teams_user_configurations(),
        scopes=SCOPES["directory_read"],
        cache_key=f"user_team_config:{upn}",
        ttl=settings.cache_ttl_policies,
        params={
            "$filter": f"userPrincipalName eq '{upn}'",
            "$select": "id,userPrincipalName,effectivePolicyAssignments",
            "$top": "1",
        },
    )
    configs = data.get("value", [])
    if not configs:
        raise NotFoundError(f"No Teams user configuration found for {upn}")
    config = configs[0]
    effective_assignments = config.get("effectivePolicyAssignments", [])

    policies: list[dict[str, Any]] = []
    for assignment in effective_assignments:
        policy_assignment = assignment.get("policyAssignment") or {}
        policies.append(
            {
                "policyType": assignment.get("policyType"),
                "policyName": policy_assignment.get("displayName", "Global (Org-wide default)"),
                "assignmentType": policy_assignment.get("assignmentType"),
                "policyId": policy_assignment.get("policyId"),
                "groupId": policy_assignment.get("groupId"),
            }
        )

    lines = [f"## Assigned Policies: {upn}"]
    for policy in policies:
        name = policy.get("policyName", "Global (Org-wide default)")
        assignment_type = policy.get("assignmentType") or "unknown"
        lines.append(f"- **{policy.get('policyType', '?')}:** {name} [{assignment_type}]")
    if not policies:
        lines.append("- No effective policy assignments returned for this user")

    return {
        "upn": upn,
        "user_id": config.get("id"),
        "user_principal_name": config.get("userPrincipalName", upn),
        "assigned_policies": policies,
        "count": len(policies),
        "markdown": "\n".join(lines),
    }


async def get_user_overview(upn: str) -> dict[str, Any]:
    profile_coro = get_user_profile(upn)
    teams_coro = list_user_teams(upn)

    profile_result, teams_result = await asyncio.gather(profile_coro, teams_coro, return_exceptions=True)

    profile: dict[str, Any] = profile_result if not isinstance(profile_result, Exception) else {"error": str(profile_result)}
    teams: dict[str, Any] = teams_result if not isinstance(teams_result, Exception) else {"error": str(teams_result)}

    presence: dict[str, Any] = {}
    if "id" in profile:
        try:
            presence = await graph_get(
                endpoints.user_presence(profile["id"]),
                scopes=SCOPES["presence_read"],
                cache_key=f"presence:{profile['id']}",
                ttl=settings.cache_ttl_presence,
            )
        except Exception as exc:
            presence = {"error": str(exc)}

    markdown = _build_overview_markdown(upn, profile, presence, teams)

    return {
        "upn": upn,
        "profile": profile,
        "presence": presence,
        "teams": teams,
        "markdown": markdown,
    }


def _build_overview_markdown(
    upn: str,
    profile: dict[str, Any],
    presence: dict[str, Any],
    teams: dict[str, Any],
) -> str:
    lines = [f"## User Overview: {profile.get('displayName', upn)}"]
    lines.append(f"- **UPN:** {upn}")
    lines.append(f"- **Department:** {profile.get('department', 'N/A')}")
    lines.append(f"- **Job Title:** {profile.get('jobTitle', 'N/A')}")
    lines.append(f"- **Office:** {profile.get('officeLocation', 'N/A')}")
    avail = presence.get("availability", "Unknown")
    lines.append(f"- **Presence:** {avail}")
    team_list = teams.get("value", [])
    lines.append(f"\n### Teams ({len(team_list)})")
    for t in team_list[:10]:
        display = t.get("displayName", "?")
        team_id = t.get("id", "?")
        lines.append(f"  - **{display}** (`{team_id}`)")
    if len(team_list) > 10:
        lines.append(f"  - ...and {len(team_list) - 10} more")
    return "\n".join(lines)


async def search_user(query: str) -> dict[str, Any]:
    """Search for users by display name, email prefix, or UPN fragment."""
    data = await graph_get(
        "/users",
        scopes=SCOPES["user_read"],
        params={
            "$search": f'"displayName:{query}" OR "userPrincipalName:{query}"',
            "$select": "id,displayName,userPrincipalName,jobTitle,department,mail",
            "$top": "10",
        },
        extra_headers={"ConsistencyLevel": "eventual"},
    )
    users = data.get("value", [])
    lines = [f"## Search results for '{query}' ({len(users)} found)"]
    for u in users:
        lines.append(
            f"- **{u.get('displayName', '?')}** — `{u.get('userPrincipalName', '?')}` | "
            f"{u.get('jobTitle', '')} | {u.get('department', '')}"
        )
    if not users:
        lines.append("No users found. Try a different name or email fragment.")
    return {
        "query": query,
        "users": users,
        "count": len(users),
        "markdown": "\n".join(lines),
    }
