from __future__ import annotations

from typing import Any

from mcp_msteams.graph import endpoints
from mcp_msteams.graph.client import graph_get
from mcp_msteams.security.permissions import SCOPES
from mcp_msteams.services.users_service import get_user_assigned_policies


async def _get_voice_context(upn: str) -> tuple[dict[str, Any], dict[str, Any]]:
    profile = await graph_get(
        endpoints.user(upn),
        scopes=SCOPES["user_read"],
        params={
            "$select": "id,displayName,userPrincipalName,businessPhones,mobilePhone,officeLocation,jobTitle,assignedLicenses"
        },
        cache_key=f"voice-user:{upn}",
        ttl=300,
    )
    policies = await get_user_assigned_policies(upn)
    return profile, policies


async def get_voice_configuration(upn: str) -> dict[str, Any]:
    profile, policies = await _get_voice_context(upn)
    calling_policies = [
        policy for policy in policies.get("assigned_policies", [])
        if "Calling" in str(policy.get("policyType", "")) or "Dial" in str(policy.get("policyType", "")) or "Voice" in str(policy.get("policyType", ""))
    ]
    lines = [f"## Voice Configuration: {upn}"]
    lines.append(f"- **Business phones:** {len(profile.get('businessPhones', []))}")
    lines.append(f"- **Mobile phone:** {'set' if profile.get('mobilePhone') else 'not set'}")
    lines.append(f"- **Assigned licenses:** {len(profile.get('assignedLicenses', []))}")
    lines.append(f"- **Voice-related policies:** {len(calling_policies)}")
    for policy in calling_policies:
        lines.append(f"- **{policy.get('policyType', '?')}:** {policy.get('policyName', '?')}")
    return {
        "upn": upn,
        "profile": profile,
        "voice_policies": calling_policies,
        "markdown": "\n".join(lines),
    }


async def validate_voice_routing(upn: str) -> dict[str, Any]:
    profile, policies = await _get_voice_context(upn)
    voice_policies = {policy.get("policyType"): policy.get("policyName") for policy in policies.get("assigned_policies", [])}
    checks: list[dict[str, Any]] = []
    checks.append(
        {
            "name": "has_phone_number",
            "pass": bool(profile.get("businessPhones") or profile.get("mobilePhone")),
            "details": "User has at least one phone number on profile",
        }
    )
    checks.append(
        {
            "name": "has_calling_policy",
            "pass": any("Calling" in str(key) for key in voice_policies),
            "details": "User has a Teams calling-related policy assignment",
        }
    )
    checks.append(
        {
            "name": "has_voice_routing_policy",
            "pass": any("VoiceRouting" in str(key) for key in voice_policies),
            "details": "User has a voice routing policy assignment",
        }
    )
    failed = [check for check in checks if not check["pass"]]
    lines = [f"## Voice Routing Validation: {upn}"]
    lines.append(f"- **Checks passed:** {len(checks) - len(failed)}/{len(checks)}")
    for check in checks:
        lines.append(f"- **{check['name']}:** {'PASS' if check['pass'] else 'FAIL'} | {check['details']}")
    return {
        "upn": upn,
        "checks": checks,
        "failed_checks": failed,
        "is_valid": not failed,
        "markdown": "\n".join(lines),
    }


async def detect_voice_misconfiguration(upn: str) -> dict[str, Any]:
    profile, policies = await _get_voice_context(upn)
    issues: list[dict[str, Any]] = []
    if not profile.get("businessPhones") and not profile.get("mobilePhone"):
        issues.append({"type": "NoPhoneNumber", "description": "No phone number is present on the user profile."})

    policy_map = {policy.get("policyType"): policy.get("policyName", "") for policy in policies.get("assigned_policies", [])}
    calling_policy = str(policy_map.get("TeamsCallingPolicy", ""))
    if "NoAllowedCalling" in calling_policy:
        issues.append({"type": "CallingDisabled", "description": "Calling policy appears to disable calling."})
    if "TeamsVoiceRoutingPolicy" not in policy_map:
        issues.append({"type": "MissingVoiceRoutingPolicy", "description": "No TeamsVoiceRoutingPolicy assignment found."})

    lines = [f"## Voice Misconfiguration Detection: {upn}"]
    lines.append(f"- **Issues detected:** {len(issues)}")
    for issue in issues:
        lines.append(f"- **{issue['type']}:** {issue['description']}")
    return {
        "upn": upn,
        "issues": issues,
        "issue_count": len(issues),
        "markdown": "\n".join(lines),
    }
