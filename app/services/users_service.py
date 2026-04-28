from __future__ import annotations

import asyncio
from typing import Any

from app.config import settings
from app.graph import endpoints
from app.graph.client import graph_get
from app.security.permissions import SCOPES


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
    return await graph_get(
        endpoints.user_joined_teams(upn),
        scopes=SCOPES["team_read"],
        cache_key=f"user_teams:{upn}",
        ttl=settings.cache_ttl_teams,
    )


async def get_user_assigned_policies(upn: str) -> dict[str, Any]:
    return await graph_get(
        endpoints.user_teamwork(upn),
        scopes=SCOPES["directory_read"],
        cache_key=f"user_teamwork:{upn}",
        ttl=settings.cache_ttl_policies,
    )


async def get_user_overview(upn: str) -> dict[str, Any]:
    profile_coro = get_user_profile(upn)
    teams_coro = list_user_teams(upn)

    profile_result, teams_result = await asyncio.gather(profile_coro, teams_coro, return_exceptions=True)

    profile: dict[str, Any] = profile_result if not isinstance(profile_result, Exception) else {"error": str(profile_result)}
    teams: dict[str, Any] = teams_result if not isinstance(teams_result, Exception) else {"error": str(teams_result)}

    presence: dict[str, Any] = {}
    if "id" in profile:
        try:
            presence = await get_user_presence(upn)
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
        lines.append(f"  - {t.get('displayName', t.get('id', '?'))}")
    if len(team_list) > 10:
        lines.append(f"  - ...and {len(team_list) - 10} more")
    return "\n".join(lines)
