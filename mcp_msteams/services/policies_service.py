from __future__ import annotations

import asyncio
from typing import Any

from mcp_msteams.config import settings
from mcp_msteams.graph import endpoints
from mcp_msteams.graph.client import graph_get
from mcp_msteams.security.permissions import SCOPES


async def get_user_assigned_policies(upn: str) -> dict[str, Any]:
    data = await graph_get(
        endpoints.user_teamwork(upn),
        scopes=SCOPES["directory_read"],
        cache_key=f"user_teamwork:{upn}",
        ttl=settings.cache_ttl_policies,
    )
    policies = data.get("assignedPolicies", [])
    lines = [f"## Assigned Policies: {upn}"]
    for p in policies:
        lines.append(f"- **{p.get('policyType', '?')}:** {p.get('policyName', 'Global (Org-wide default)')}")
    if not policies:
        lines.append("- No custom policies assigned (using org-wide defaults)")
    return {
        "upn": upn,
        "assigned_policies": policies,
        "count": len(policies),
        "markdown": "\n".join(lines),
    }


async def compare_user_policies(upn1: str, upn2: str) -> dict[str, Any]:
    r1, r2 = await asyncio.gather(
        get_user_assigned_policies(upn1),
        get_user_assigned_policies(upn2),
        return_exceptions=True,
    )

    if isinstance(r1, Exception):
        return {"error": f"Failed to fetch policies for {upn1}: {r1}"}
    if isinstance(r2, Exception):
        return {"error": f"Failed to fetch policies for {upn2}: {r2}"}

    policies1 = {p["policyType"]: p.get("policyName", "") for p in r1.get("assigned_policies", [])}
    policies2 = {p["policyType"]: p.get("policyName", "") for p in r2.get("assigned_policies", [])}

    all_types = set(policies1) | set(policies2)
    diff: list[dict[str, Any]] = []
    for ptype in sorted(all_types):
        v1 = policies1.get(ptype, "Global (Org-wide default)")
        v2 = policies2.get(ptype, "Global (Org-wide default)")
        diff.append({"policy_type": ptype, "upn1_value": v1, "upn2_value": v2, "match": v1 == v2})

    mismatches = [d for d in diff if not d["match"]]
    lines = [f"## Policy Comparison: {upn1} vs {upn2}"]
    lines.append(f"- **Mismatches:** {len(mismatches)} of {len(diff)} policy types differ\n")
    lines.append(f"| Policy Type | {upn1} | {upn2} | Match |")
    lines.append("|---|---|---|---|")
    for d in diff:
        match_icon = "✓" if d["match"] else "✗"
        lines.append(f"| {d['policy_type']} | {d['upn1_value']} | {d['upn2_value']} | {match_icon} |")

    return {"upn1": upn1, "upn2": upn2, "diff": diff, "mismatch_count": len(mismatches), "markdown": "\n".join(lines)}


async def detect_policy_conflicts(upn: str) -> dict[str, Any]:
    data = await get_user_assigned_policies(upn)
    policies = data.get("assigned_policies", [])

    conflicts: list[dict[str, Any]] = []
    policy_map = {p.get("policyType"): p.get("policyName", "") for p in policies}

    # Known conflict: calling disabled but meeting scheduling enabled
    calling_policy = policy_map.get("TeamsCallingPolicy", "")
    meeting_policy = policy_map.get("TeamsMeetingPolicy", "")
    if "NoAllowedCalling" in str(calling_policy) and meeting_policy:
        conflicts.append({
            "type": "MeetingCallingConflict",
            "description": "Calling disabled (TeamsCallingPolicy) but meeting policy assigned — user may have scheduling issues.",
            "policies": [calling_policy, meeting_policy],
        })

    lines = [f"## Policy Conflict Detection: {upn}"]
    if conflicts:
        lines.append(f"- **{len(conflicts)} conflict(s) detected**")
        for c in conflicts:
            lines.append(f"\n### {c['type']}")
            lines.append(f"  {c['description']}")
    else:
        lines.append("- No known conflicts detected.")

    return {"upn": upn, "conflicts": conflicts, "conflict_count": len(conflicts), "markdown": "\n".join(lines)}
