from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from mcp_msteams.graph import endpoints
from mcp_msteams.graph.client import graph_get, graph_get_all
from mcp_msteams.security.permissions import SCOPES


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


async def _get_device_details(upn: str) -> list[dict[str, Any]]:
    objects = await graph_get_all(
        endpoints.user_registered_devices(upn),
        scopes=SCOPES["directory_read"],
        max_pages=5,
    )
    device_ids = [obj.get("id") for obj in objects if obj.get("id")]
    details: list[dict[str, Any]] = []
    for device_id in device_ids:
        device = await graph_get(
            endpoints.device(device_id),
            scopes=SCOPES["directory_read"],
            cache_key=f"device:{device_id}",
            ttl=300,
        )
        details.append(device)
    return details


async def get_user_devices(upn: str) -> dict[str, Any]:
    devices = await _get_device_details(upn)
    lines = [f"## Registered Devices: {upn} ({len(devices)})"]
    for device in devices:
        lines.append(
            f"- **{device.get('displayName', device.get('id', '?'))}** | "
            f"{device.get('operatingSystem', 'unknown')} {device.get('operatingSystemVersion', '')}".rstrip()
        )
    return {
        "upn": upn,
        "devices": devices,
        "count": len(devices),
        "markdown": "\n".join(lines),
    }


async def detect_device_problems(upn: str) -> dict[str, Any]:
    devices = await _get_device_details(upn)
    now = datetime.now(tz=timezone.utc)
    problems: list[dict[str, Any]] = []
    for device in devices:
        reasons: list[str] = []
        if device.get("accountEnabled") is False:
            reasons.append("device disabled")
        if device.get("isCompliant") is False:
            reasons.append("device marked non-compliant")
        last_sign_in = _parse_datetime(device.get("approximateLastSignInDateTime"))
        if last_sign_in and now - last_sign_in > timedelta(days=90):
            reasons.append("stale sign-in (>90 days)")
        if reasons:
            problems.append(
                {
                    "id": device.get("id"),
                    "displayName": device.get("displayName"),
                    "reasons": reasons,
                }
            )

    lines = [f"## Device Problem Detection: {upn}"]
    lines.append(f"- **Devices analyzed:** {len(devices)}")
    lines.append(f"- **Devices with issues:** {len(problems)}")
    for problem in problems:
        lines.append(f"- **{problem.get('displayName', problem.get('id', '?'))}:** {', '.join(problem['reasons'])}")
    return {
        "upn": upn,
        "devices_analyzed": len(devices),
        "problems": problems,
        "problem_count": len(problems),
        "markdown": "\n".join(lines),
    }
