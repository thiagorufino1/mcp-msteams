from __future__ import annotations

import json
from typing import Any

from mcp_msteams.config import settings
from mcp_msteams.graph import endpoints
from mcp_msteams.graph.client import graph_get, graph_get_all
from mcp_msteams.security.permissions import SCOPES


async def list_team_channels(team_id: str) -> dict[str, Any]:
    channels = await graph_get_all(
        endpoints.team_channels(team_id),
        scopes=SCOPES["channel_read"],
    )
    markdown = _channels_markdown(team_id, channels)
    return {"team_id": team_id, "channels": channels, "count": len(channels), "markdown": markdown}


async def list_team_members(team_id: str) -> dict[str, Any]:
    members = await graph_get_all(
        endpoints.group_members(team_id),
        scopes=SCOPES["team_read"],
    )
    markdown = _members_markdown(team_id, members, role="member")
    return {"team_id": team_id, "members": members, "count": len(members), "markdown": markdown}


async def get_team_owners(team_id: str) -> dict[str, Any]:
    owners = await graph_get_all(
        endpoints.group_owners(team_id),
        scopes=SCOPES["team_read"],
    )
    markdown = _members_markdown(team_id, owners, role="owner")
    return {"team_id": team_id, "owners": owners, "count": len(owners), "markdown": markdown}


async def get_team_settings(team_id: str) -> dict[str, Any]:
    data = await graph_get(
        endpoints.team(team_id),
        scopes=SCOPES["team_read"],
        cache_key=f"team:{team_id}",
        ttl=settings.cache_ttl_teams,
    )
    display = data.get("displayName", team_id)
    markdown = f"## Team Settings: {display}\n\n```json\n{json.dumps(data, indent=2)}\n```"
    return {**data, "markdown": markdown}


async def get_channel_settings(team_id: str, channel_id: str) -> dict[str, Any]:
    data = await graph_get(
        endpoints.team_channel(team_id, channel_id),
        scopes=SCOPES["channel_read"],
        cache_key=f"channel:{team_id}:{channel_id}",
        ttl=settings.cache_ttl_teams,
    )
    return {**data, "markdown": f"## Channel: {data.get('displayName', channel_id)}\n- **Type:** {data.get('membershipType', 'standard')}\n- **Description:** {data.get('description', 'N/A')}"}


async def check_private_shared_channels(team_id: str) -> dict[str, Any]:
    channels = await graph_get_all(
        endpoints.team_channels(team_id),
        scopes=SCOPES["channel_read"],
    )
    private = [c for c in channels if c.get("membershipType") == "private"]
    shared = [c for c in channels if c.get("membershipType") == "shared"]
    lines = [f"## Private & Shared Channels in Team {team_id}"]
    lines.append(f"- **Private channels:** {len(private)}")
    lines.append(f"- **Shared channels:** {len(shared)}")
    if private:
        lines.append("\n### Private Channels")
        for c in private:
            lines.append(f"  - {c.get('displayName', c['id'])}")
    if shared:
        lines.append("\n### Shared Channels")
        for c in shared:
            lines.append(f"  - {c.get('displayName', c['id'])}")
    return {"team_id": team_id, "private_channels": private, "shared_channels": shared, "markdown": "\n".join(lines)}


async def detect_orphaned_team(team_id: str) -> dict[str, Any]:
    members = await graph_get_all(
        endpoints.group_members(team_id),
        scopes=SCOPES["team_read"],
    )
    is_orphaned = len(members) == 0
    status = "ORPHANED — no members" if is_orphaned else f"OK — {len(members)} member(s)"
    return {
        "team_id": team_id,
        "is_orphaned": is_orphaned,
        "member_count": len(members),
        "status": status,
        "markdown": f"## Orphaned Team Check: {team_id}\n- **Status:** {status}",
    }


async def detect_team_without_owner(team_id: str) -> dict[str, Any]:
    owners = await graph_get_all(
        endpoints.group_owners(team_id),
        scopes=SCOPES["team_read"],
    )
    has_no_owner = len(owners) == 0
    status = "NO OWNER — team has no owners" if has_no_owner else f"OK — {len(owners)} owner(s)"
    return {
        "team_id": team_id,
        "has_no_owner": has_no_owner,
        "owner_count": len(owners),
        "owners": owners,
        "status": status,
        "markdown": f"## Owner Check: {team_id}\n- **Status:** {status}",
    }


def _channels_markdown(team_id: str, channels: list[dict[str, Any]]) -> str:
    lines = [f"## Channels in Team {team_id} ({len(channels)} total)"]
    for c in channels:
        ctype = c.get("membershipType", "standard")
        lines.append(f"- **{c.get('displayName', c.get('id', '?'))}** [{ctype}]")
    return "\n".join(lines)


def _members_markdown(team_id: str, members: list[dict[str, Any]], role: str) -> str:
    lines = [f"## Team {role.capitalize()}s: {team_id} ({len(members)} total)"]
    for m in members:
        name = m.get("displayName", m.get("userPrincipalName", m.get("id", "?")))
        upn = m.get("userPrincipalName", "")
        lines.append(f"- {name} ({upn})" if upn else f"- {name}")
    return "\n".join(lines)
