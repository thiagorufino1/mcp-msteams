from __future__ import annotations

import csv
import io
from typing import Any

import httpx

from mcp_msteams.graph import endpoints
from mcp_msteams.graph.errors import NotFoundError
from mcp_msteams.security.auth import get_token
from mcp_msteams.security.permissions import SCOPES

_PERIOD_OPTIONS = {"7": "D7", "30": "D30", "90": "D90"}

_DURATION_FIELDS = {
    "Audio Duration In Seconds": "audio_seconds",
    "Video Duration In Seconds": "video_seconds",
    "Screen Share Duration In Seconds": "screen_share_seconds",
}
_COUNT_FIELDS = {
    "Call Count": "call_count",
    "Meeting Count": "meeting_count",
    "Meetings Organized Count": "meetings_organized",
    "Meetings Attended Count": "meetings_attended",
    "Team Chat Message Count": "team_chat_messages",
    "Private Chat Message Count": "private_chat_messages",
}


def _fmt_duration(seconds: int) -> str:
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


async def get_user_activity_report(upn: str, days: int = 7) -> dict[str, Any]:
    period_key = str(days) if str(days) in _PERIOD_OPTIONS else "7"
    period = _PERIOD_OPTIONS[period_key]
    token = get_token(SCOPES["reports"])

    # Reports API returns CSV via redirect — use a separate client without base_url
    async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
        url = f"https://graph.microsoft.com/v1.0{endpoints.teams_user_activity_detail(period)}"
        response = await client.get(
            url,
            headers={"Authorization": f"Bearer {token}", "Accept": "text/csv"},
        )
        response.raise_for_status()
        csv_text = response.text

    reader = csv.DictReader(io.StringIO(csv_text))
    user_row: dict | None = None
    for row in reader:
        row_upn = (row.get("User Principal Name") or row.get("userPrincipalName") or "").strip().lower()
        if row_upn == upn.lower():
            user_row = row
            break

    if not user_row:
        raise NotFoundError(f"No activity data found for {upn} in the last {period_key} days.")

    counts = {v: int(user_row.get(k, 0) or 0) for k, v in _COUNT_FIELDS.items()}
    durations = {v: int(user_row.get(k, 0) or 0) for k, v in _DURATION_FIELDS.items()}

    total_call_seconds = durations["audio_seconds"] + durations["video_seconds"]
    total_seconds = total_call_seconds + durations["screen_share_seconds"]

    total_h = total_call_seconds // 3600
    total_m = (total_call_seconds % 3600) // 60

    lines = [f"## Atividade de ligações e reuniões semanal: {upn}"]
    lines.append(f"**Período:** últimos {period_key} dias | **Última atividade:** {user_row.get('Last Activity Date', 'N/A')}")
    lines.append("")
    lines.append("| Métrica | Valor |")
    lines.append("|---------|-------|")
    lines.append(f"| Reuniões (meetings) | {counts['meeting_count']} |")
    lines.append(f"| Chamadas 1:1 (calls) | {counts['call_count']} |")
    lines.append(f"| **Total de interações** | **{counts['meeting_count'] + counts['call_count']}** |")
    lines.append(f"| Reuniões organizadas | {counts['meetings_organized']} |")
    lines.append(f"| Reuniões como participante | {counts['meetings_attended']} |")
    lines.append(f"| **Duração total (h:mm)** | **{total_h}h{total_m:02d}m** |")
    lines.append(f"| Duração em áudio | {_fmt_duration(durations['audio_seconds'])} |")
    lines.append(f"| Duração em vídeo | {_fmt_duration(durations['video_seconds'])} |")
    lines.append(f"| Duração em screen share | {_fmt_duration(durations['screen_share_seconds'])} |")

    return {
        "upn": upn,
        "period_days": int(period_key),
        "last_activity": user_row.get("Last Activity Date"),
        "counts": counts,
        "durations_seconds": durations,
        "total_call_duration": _fmt_duration(total_call_seconds),
        "total_duration": _fmt_duration(total_seconds),
        "markdown": "\n".join(lines),
    }
