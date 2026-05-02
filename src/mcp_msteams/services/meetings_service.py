from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

_BRT = timezone(timedelta(hours=-3))

from mcp_msteams.graph import endpoints
from mcp_msteams.graph.client import graph_get, graph_get_all
from mcp_msteams.graph.errors import AuthError, GraphError, NotFoundError
from mcp_msteams.services.calls_service import _get_user_call_records
from mcp_msteams.services.users_service import get_user_profile
from mcp_msteams.security.permissions import SCOPES
from mcp_msteams.utils.date_utils import graph_date_filter


def _to_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _meeting_code(join_url: str | None) -> str:
    if not join_url:
        return "N/A"
    # Extract thread ID from Teams join URL: /19:meeting_<id>@thread.v2/
    match = re.search(r"/(19%3[Aa][^/]+)/", join_url)
    if match:
        from urllib.parse import unquote
        return unquote(match.group(1))
    return "N/A"


async def get_recent_meetings(upn: str, days: int = 7) -> dict[str, Any]:
    source = "onlineMeetings"
    profile = await get_user_profile(upn)
    user_ref = profile.get("id") or upn
    try:
        meetings = await graph_get_all(
            endpoints.user_online_meetings(user_ref),
            scopes=SCOPES["reports"],
            params={"$filter": graph_date_filter("startDateTime", days)},
            max_pages=5,
        )
        meetings = sorted(meetings, key=lambda meeting: meeting.get("startDateTime", ""), reverse=True)
    except GraphError as e:
        if isinstance(e, AuthError) or e.status_code == 403:
            # Fallback to Call Records API (groupCalls) because Application Access Policy is missing
            source = "callRecords_fallback"
            try:
                records = await _get_user_call_records(upn, days)
            except GraphError as fallback_exc:
                raise GraphError(
                    "onlineMeetings API requires Application Access Policy "
                    "(New-CsApplicationAccessPolicy / Grant-CsApplicationAccessPolicy). "
                    f"callRecords fallback also failed: {fallback_exc}"
                ) from fallback_exc
            meetings = records
        else:
            raise

    _TYPE_LABEL = {"groupcall": "Reunião", "peertopeer": "Chamada 1:1"}

    lines = [f"## Chamadas e Reuniões: {upn} (últimos {days} dias)"]
    lines.append(f"- **Source:** {source}")
    lines.append(f"- **Total:** {len(meetings)}")
    grouped = {"groupCall": sum(1 for m in meetings if str(m.get("type","")).lower() in ("groupcall","grouppall")),
               "peerToPeer": sum(1 for m in meetings if str(m.get("type","")).lower() == "peertopeer")}
    lines.append(f"- **Reuniões (groupCall):** {grouped['groupCall']} | **Chamadas 1:1 (peerToPeer):** {grouped['peerToPeer']}")
    lines.append("")
    lines.append("| # | Tipo | Call ID | Start (BRT) | End (BRT) | Meeting Code | Participantes | Activity Type | Duração (min) |")
    lines.append("|---|------|---------|-------------|-----------|--------------|--------------|---------------|---------------|")
    for i, meeting in enumerate(meetings[:20], 1):
        start_dt = _to_datetime(meeting.get("startDateTime"))
        end_dt = _to_datetime(meeting.get("endDateTime"))
        duration = (
            round((end_dt - start_dt).total_seconds() / 60, 1)
            if start_dt and end_dt else "?"
        )
        start_str = start_dt.astimezone(_BRT).strftime("%d/%m %H:%M") if start_dt else "?"
        end_str = end_dt.astimezone(_BRT).strftime("%d/%m %H:%M") if end_dt else "?"
        call_id = meeting.get("id", "?")
        meeting_code = _meeting_code(meeting.get("joinWebUrl"))
        participants_v2 = meeting.get("participants_v2") or []
        participant_count = len(participants_v2)
        modalities = meeting.get("modalities") or []
        activity_type = ", ".join(modalities) if modalities else meeting.get("type", "?")
        call_type_raw = str(meeting.get("type", "")).lower()
        tipo = _TYPE_LABEL.get(call_type_raw, meeting.get("type", "?"))

        lines.append(
            f"| {i} | {tipo} | `{call_id}` | {start_str} | {end_str} | `{meeting_code}` "
            f"| {participant_count} | {activity_type} | {duration} |"
        )

    if len(meetings) > 20:
        lines.append(f"\n*...and {len(meetings) - 20} more*")

    summary = [
        {"id": m.get("id"), "type": m.get("type"), "start": m.get("startDateTime"),
         "end": m.get("endDateTime"),
         "organizer": ((m.get("organizer_v2") or {}).get("identity", {}).get("user", {}).get("displayName")),
         "participant_count": len(m.get("participants_v2") or [])}
        for m in meetings
    ]
    return {
        "upn": upn,
        "days": days,
        "source": source,
        "count": len(meetings),
        "group_call_count": grouped["groupCall"],
        "peer_to_peer_count": grouped["peerToPeer"],
        "meetings": summary,
        "markdown": "\n".join(lines),
    }


async def get_meeting_participants(call_id: str) -> dict[str, Any]:
    record = await graph_get(
        f"{endpoints.call_record(call_id)}?$expand=participants_v2",
        scopes=SCOPES["call_records"],
        cache_key=f"callrecord:participants:{call_id}",
        ttl=60,
    )
    participants_v2 = record.get("participants_v2") or []
    start_dt = _to_datetime(record.get("startDateTime"))
    end_dt = _to_datetime(record.get("endDateTime"))
    duration = (
        round((end_dt - start_dt).total_seconds() / 60, 1)
        if start_dt and end_dt else None
    )
    start_brt = start_dt.astimezone(_BRT).strftime("%d/%m/%Y %H:%M") if start_dt else "N/A"

    lines = [f"## Participants: {call_id}"]
    lines.append(f"- **Start (BRT):** {start_brt}")
    if duration:
        lines.append(f"- **Duration (min):** {duration}")
    lines.append(f"- **Total participants:** {len(participants_v2)}")
    lines.append("")
    lines.append("| # | Name | UPN |")
    lines.append("|---|------|-----|")
    participant_list = []
    for i, p in enumerate(participants_v2, 1):
        user = (p.get("identity") or {}).get("user") or {}
        name = user.get("displayName") or p.get("id", "?")
        upn = user.get("userPrincipalName", "")
        lines.append(f"| {i} | {name} | {upn} |")
        participant_list.append({"id": p.get("id"), "name": name, "upn": upn})

    return {
        "call_id": call_id,
        "participant_count": len(participants_v2),
        "participants": participant_list,
        "markdown": "\n".join(lines),
    }
