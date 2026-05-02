from __future__ import annotations

import asyncio
import json
from typing import Any

from mcp_msteams.config import settings
from mcp_msteams.graph import endpoints
from mcp_msteams.graph.client import graph_get, graph_get_all, graph_get_paged
from mcp_msteams.security.permissions import SCOPES

_TEAMS_FILTER = "resourceProvisioningOptions/Any(x:x eq 'Team')"
_CONSISTENCY_HEADERS = {"ConsistencyLevel": "eventual"}
_TEAMS_SELECT = "id,displayName,visibility,createdDateTime,description"
_TEAM_COUNTS_CONCURRENCY = settings.graph_team_counts_concurrency
_TEAM_RANKINGS_CONCURRENCY = settings.graph_team_rankings_concurrency
_TEAM_SCAN_MAX_TEAMS = settings.graph_team_scan_max_teams


# ── existing per-team functions ──────────────────────────────────────────────

async def list_team_channels(team_id: str) -> dict[str, Any]:
    channels = await graph_get_all(
        endpoints.team_channels(team_id),
        scopes=SCOPES["channel_read"],
    )
    markdown = _channels_markdown(team_id, channels)
    return {"team_id": team_id, "channels": channels, "count": len(channels), "markdown": markdown}


async def list_team_members(team_id: str) -> dict[str, Any]:
    members = await graph_get_all(
        endpoints.team_members(team_id),
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
            lines.append(f"  - **{c.get('displayName', '?')}** (`{c['id']}`)")
    if shared:
        lines.append("\n### Shared Channels")
        for c in shared:
            lines.append(f"  - **{c.get('displayName', '?')}** (`{c['id']}`)")
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


# ── tenant-wide analytics — private helpers ───────────────────────────────────

async def _count_teams(extra_filter: str = "") -> int:
    """Return total count of Teams-enabled groups matching an optional extra filter.
    Uses $count=true with ConsistencyLevel:eventual — requires Group.Read.All.
    Returns -1 on error.
    """
    filt = f"{_TEAMS_FILTER} and {extra_filter}" if extra_filter else _TEAMS_FILTER
    try:
        data = await graph_get(
            "/groups",
            scopes=SCOPES["team_read"],
            params={"$filter": filt, "$select": "id", "$top": 1, "$count": "true"},
            extra_headers=_CONSISTENCY_HEADERS,
        )
        return int(data.get("@odata.count", -1))
    except Exception:
        return -1


async def _get_member_count(group_id: str) -> int:
    """Return the number of members for a group using @odata.count. Returns 0 on error."""
    try:
        data = await graph_get(
            endpoints.group_members(group_id),
            scopes=SCOPES["team_read"],
            params={"$count": "true", "$top": 1, "$select": "id"},
            extra_headers=_CONSISTENCY_HEADERS,
        )
        return int(data.get("@odata.count", 0))
    except Exception:
        return 0


async def _get_owner_count(group_id: str) -> int:
    """Return the number of owners for a group using @odata.count. Returns 0 on error."""
    try:
        data = await graph_get(
            endpoints.group_owners(group_id),
            scopes=SCOPES["team_read"],
            params={"$count": "true", "$top": 1, "$select": "id"},
            extra_headers=_CONSISTENCY_HEADERS,
        )
        return int(data.get("@odata.count", 0))
    except Exception:
        return 0


async def _get_visibility_counts() -> dict[str, int]:
    """Paginate through all Teams-enabled groups and count by visibility (client-side).

    Graph API does not support `$filter=visibility eq 'Public'` for groups.
    Uses $top=999 (max allowed with ConsistencyLevel:eventual) to minimise
    the number of serial page fetches (~5 pages for a 4400-team tenant).
    """
    result = await graph_get_paged(
        "/groups",
        scopes=SCOPES["team_read"],
        params={
            "$filter": _TEAMS_FILTER,
            "$select": "id,visibility",
            "$top": 999,
            "$count": "true",
        },
        extra_headers=_CONSISTENCY_HEADERS,
        max_pages=10,
    )
    counts: dict[str, int] = {}
    for team in result["items"]:
        v = team.get("visibility") or "Unknown"
        counts[v] = counts.get(v, 0) + 1
    return counts


# ── tenant-wide analytics — public functions ─────────────────────────────────

async def list_all_teams(
    top: int = 20,
    skip: int = 0,
    privacy: str | None = None,
    include_counts: bool = True,
) -> dict[str, Any]:
    """Return one page of Teams-enabled groups with optional member/owner counts.

    When `privacy` is set, fetches a larger batch and filters client-side since
    Graph API does not support $filter=visibility for groups.
    """
    # Fetch more when filtering by privacy (client-side filter needs a larger pool)
    fetch_top = min(top * 4, 100) if privacy else top
    params: dict[str, Any] = {
        "$filter": _TEAMS_FILTER,
        "$select": _TEAMS_SELECT,
        "$top": fetch_top,
        "$count": "true",
        "$orderby": "displayName",
    }
    if skip and not privacy:
        params["$skip"] = skip
    data = await graph_get(
        "/groups",
        scopes=SCOPES["team_read"],
        params=params,
        extra_headers=_CONSISTENCY_HEADERS,
    )
    teams: list[dict[str, Any]] = data.get("value", [])
    total: int | None = data.get("@odata.count")
    has_more = "@odata.nextLink" in data

    if privacy:
        teams = [t for t in teams if (t.get("visibility") or "").lower() == privacy.lower()][:top]
        has_more = len(teams) == top

    if include_counts and teams:
        sem = asyncio.Semaphore(_TEAM_COUNTS_CONCURRENCY)

        async def _count_pair(team_id: str) -> tuple[int, int]:
            async with sem:
                return await asyncio.gather(_get_member_count(team_id), _get_owner_count(team_id))

        results = await asyncio.gather(
            *[_count_pair(t["id"]) for t in teams]
        )
        for team, (mc, oc) in zip(teams, results):
            team["_memberCount"] = mc
            team["_ownerCount"] = oc

    markdown = _all_teams_markdown(teams, total, skip, include_counts)
    return {"teams": teams, "count": len(teams), "total": total, "has_more": has_more, "markdown": markdown}


async def get_tenant_teams_stats() -> dict[str, Any]:
    """Consolidated tenant stats: total, visibility breakdown, and health indicators.

    Runs 3 concurrent operations:
    1. Total Teams-enabled group count ($count query).
    2. Orphaned groups count (owners/$count eq 0 filter).
    3. Full visibility scan (paginates all groups client-side — may take a few seconds).
    """
    total, orphaned_count, vis_counts = await asyncio.gather(
        _count_teams(),
        _count_teams("owners/$count eq 0"),
        _get_visibility_counts(),
    )
    stats: dict[str, Any] = {
        "total_teams": total,
        "by_visibility": {
            "public": vis_counts.get("Public", 0),
            "private": vis_counts.get("Private", 0),
        },
        "health": {
            "orphaned_no_owners": orphaned_count,
            "no_members": "use list_teams_without_members",
        },
    }
    return {**stats, "markdown": _tenant_stats_markdown(stats)}


async def list_orphaned_teams(top: int = 20) -> dict[str, Any]:
    """List Teams with no owners. Always includes member count per team."""
    filt = f"{_TEAMS_FILTER} and owners/$count eq 0"
    data = await graph_get(
        "/groups",
        scopes=SCOPES["team_read"],
        params={
            "$filter": filt,
            "$select": _TEAMS_SELECT,
            "$top": top,
            "$count": "true",
            "$orderby": "displayName",
        },
        extra_headers=_CONSISTENCY_HEADERS,
    )
    teams: list[dict[str, Any]] = data.get("value", [])
    total: int | None = data.get("@odata.count")
    # Always include member count in orphaned team summaries
    if teams:
        counts = await asyncio.gather(*[_get_member_count(t["id"]) for t in teams])
        for team, count in zip(teams, counts):
            team["_memberCount"] = count
    return {
        "teams": teams,
        "count": len(teams),
        "total": total,
        "markdown": _orphaned_teams_markdown(teams, total),
    }


async def list_teams_without_members(top: int = 20) -> dict[str, Any]:
    """Paginate through ALL Teams checking member counts, collecting those with 0 members.

    Graph API does not support `members/$count eq 0` as a $filter clause.
    This function scans ALL teams in pages of 100, checks member counts in parallel
    (max 20 concurrent), and reports the complete total found.

    `top` controls how many results are LISTED — it does NOT stop the scan early.
    The scan always runs to completion (or up to the configured scan cap) to provide an accurate total.
    """
    sem = asyncio.Semaphore(_TEAM_COUNTS_CONCURRENCY)

    async def _safe_count(group_id: str) -> int:
        async with sem:
            return await _get_member_count(group_id)

    found: list[dict[str, Any]] = []
    next_url: str | None = "/groups"
    current_params: dict[str, Any] | None = {
        "$filter": _TEAMS_FILTER,
        "$select": _TEAMS_SELECT,
        "$top": 100,
        "$count": "true",
        "$orderby": "displayName",
    }
    total_tenant: int | None = None
    teams_scanned = 0
    max_scan = _TEAM_SCAN_MAX_TEAMS

    while next_url and teams_scanned < max_scan:
        data = await graph_get(
            next_url,
            scopes=SCOPES["team_read"],
            params=current_params,
            extra_headers=_CONSISTENCY_HEADERS,
        )
        if total_tenant is None:
            total_tenant = data.get("@odata.count")
        batch: list[dict[str, Any]] = data.get("value", [])
        teams_scanned += len(batch)

        if batch:
            counts = await asyncio.gather(*[_safe_count(t["id"]) for t in batch])
            empty = [t for t, c in zip(batch, counts) if c == 0]
            found.extend(empty)

        next_url = data.get("@odata.nextLink")
        current_params = None  # nextLink carries params

    total_found = len(found)
    is_complete = next_url is None  # no nextLink = all pages exhausted

    if is_complete:
        note = f"Full scan complete — all {teams_scanned} teams checked."
    else:
        note = (
            f"Partial scan — {teams_scanned} of {total_tenant} teams checked "
            f"(tenant exceeds {max_scan} team limit)."
        )

    return {
        "teams": found[:top],
        "count": total_found,
        "listed": min(top, total_found),
        "teams_scanned": teams_scanned,
        "total_tenant": total_tenant,
        "is_complete_scan": is_complete,
        "markdown": _no_members_teams_markdown(found[:top], total_found, note),
    }


async def list_teams_by_member_count(top: int = 10) -> dict[str, Any]:
    """Full-tenant scan to rank Teams by member count.

    Two-phase approach for maximum throughput:
    - Phase 1: Paginate all team metadata using $top=999 (~5 pages for 4400 teams).
    - Phase 2: Resolve all member counts in parallel (semaphore 100, max_connections 100).
    Estimated time: ~2s pagination + ~13s counts = ~15s for a 4400-team tenant.
    """
    # Phase 1 — collect all team metadata (large page size = fewer serial requests)
    paged = await graph_get_paged(
        "/groups",
        scopes=SCOPES["team_read"],
        params={
            "$filter": _TEAMS_FILTER,
            "$select": _TEAMS_SELECT,
            "$top": 999,
            "$count": "true",
        },
        extra_headers=_CONSISTENCY_HEADERS,
        max_pages=10,
    )
    all_teams: list[dict[str, Any]] = paged["items"]
    total_tenant: int | None = paged["total"]
    teams_scanned = len(all_teams)
    is_complete = not paged["has_more"]

    # Phase 2 — resolve member counts in parallel with higher concurrency
    sem = asyncio.Semaphore(_TEAM_RANKINGS_CONCURRENCY)

    async def _safe_count(group_id: str) -> int:
        async with sem:
            return await _get_member_count(group_id)

    if all_teams:
        counts = await asyncio.gather(*[_safe_count(t["id"]) for t in all_teams])
        for team, count in zip(all_teams, counts):
            team["_memberCount"] = count

    all_teams.sort(key=lambda t: t.get("_memberCount", 0), reverse=True)
    top_teams = all_teams[:top]

    note = (
        f"Full scan — all {teams_scanned} teams checked."
        if is_complete
        else f"Partial scan — {teams_scanned} of {total_tenant} teams checked."
    )

    return {
        "teams": top_teams,
        "count": len(top_teams),
        "teams_scanned": teams_scanned,
        "total_tenant": total_tenant,
        "is_complete_scan": is_complete,
        "note": note,
        "markdown": _top_teams_by_members_markdown(top_teams, note),
    }


# ── markdown helpers (per-team) ───────────────────────────────────────────────

def _channels_markdown(team_id: str, channels: list[dict[str, Any]]) -> str:
    lines = [f"## Channels in Team {team_id} ({len(channels)} total)"]
    for c in channels:
        ctype = c.get("membershipType", "standard")
        display = c.get("displayName", "?")
        channel_id = c.get("id", "?")
        lines.append(f"- **{display}** (`{channel_id}`) [{ctype}]")
    return "\n".join(lines)


def _members_markdown(team_id: str, members: list[dict[str, Any]], role: str) -> str:
    lines = [f"## Team {role.capitalize()}s: {team_id} ({len(members)} total)"]
    for m in members:
        name = m.get("displayName", m.get("userPrincipalName", m.get("email", m.get("id", "?"))))
        principal = m.get("userPrincipalName") or m.get("email") or m.get("userId", "")
        lines.append(f"- {name} ({principal})" if principal else f"- {name}")
    return "\n".join(lines)


# ── markdown helpers (tenant analytics) ──────────────────────────────────────

def _fmt_count(n: Any) -> str:
    if isinstance(n, str):
        return n
    return str(n) if n is not None and n >= 0 else "?"


def _all_teams_markdown(
    teams: list[dict[str, Any]], total: int | None, skip: int, include_counts: bool
) -> str:
    total_str = str(total) if total is not None else "?"
    start = skip + 1
    end = skip + len(teams)
    lines = [f"## Teams ({start}–{end} of {total_str})"]
    if not teams:
        lines.append("_No teams found._")
        return "\n".join(lines)
    for t in teams:
        name = t.get("displayName", "?")
        team_id = t.get("id", "?")
        vis = t.get("visibility", "?")
        created = (t.get("createdDateTime") or "")[:10] or "?"
        line = f"- **{name}** (`{team_id}`) | {vis} | created {created}"
        if include_counts:
            mc = t.get("_memberCount", "?")
            oc = t.get("_ownerCount", "?")
            line += f" | members: {mc}, owners: {oc}"
        lines.append(line)
    return "\n".join(lines)


def _tenant_stats_markdown(stats: dict[str, Any]) -> str:
    vis = stats["by_visibility"]
    health = stats["health"]
    return "\n".join([
        "## Tenant Teams Statistics",
        f"- **Total teams:** {_fmt_count(stats['total_teams'])}",
        "",
        "### By Visibility",
        f"- Public: {_fmt_count(vis['public'])}",
        f"- Private: {_fmt_count(vis['private'])}",
        "",
        "### Health",
        f"- Orphaned (no owners): {_fmt_count(health['orphaned_no_owners'])}",
        f"- No members: {_fmt_count(health['no_members'])}",
    ])


def _orphaned_teams_markdown(teams: list[dict[str, Any]], total: int | None) -> str:
    total_str = str(total) if total is not None else str(len(teams))
    lines = [f"## Orphaned Teams — No Owners ({total_str} total)"]
    if not teams:
        lines.append("_No orphaned teams found._")
        return "\n".join(lines)
    for t in teams:
        name = t.get("displayName", "?")
        team_id = t.get("id", "?")
        created = (t.get("createdDateTime") or "")[:10] or "?"
        mc = t.get("_memberCount", "?")
        lines.append(f"- **{name}** (`{team_id}`) | created {created} | members: {mc}")
    return "\n".join(lines)


def _no_members_teams_markdown(
    teams: list[dict[str, Any]], total_found: int, note: str | None = None
) -> str:
    lines = [f"## Teams Without Members — {total_found} found"]
    if note:
        lines.append(f"_{note}_")
    if total_found > len(teams):
        lines.append(f"_Showing {len(teams)} of {total_found}. Use a larger `top` to list more._")
    if not teams:
        lines.append("_No empty teams found._")
        return "\n".join(lines)
    for t in teams:
        name = t.get("displayName", "?")
        team_id = t.get("id", "?")
        vis = t.get("visibility", "?")
        created = (t.get("createdDateTime") or "")[:10] or "?"
        lines.append(f"- **{name}** (`{team_id}`) | {vis} | created {created}")
    return "\n".join(lines)


def _top_teams_by_members_markdown(teams: list[dict[str, Any]], note: str) -> str:
    lines = [f"## Top {len(teams)} Teams by Member Count"]
    lines.append(f"_{note}_")
    lines.append("")
    if not teams:
        lines.append("_No data._")
        return "\n".join(lines)
    for i, t in enumerate(teams, 1):
        name = t.get("displayName", "?")
        team_id = t.get("id", "?")
        mc = t.get("_memberCount", 0)
        vis = t.get("visibility", "?")
        lines.append(f"{i}. **{name}** — {mc} members | {vis} | `{team_id}`")
    return "\n".join(lines)
