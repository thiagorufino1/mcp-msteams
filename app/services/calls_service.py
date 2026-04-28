from __future__ import annotations

from typing import Any

from app.config import settings
from app.graph import endpoints
from app.graph.client import graph_get
from app.security.permissions import SCOPES
from app.utils.date_utils import days_ago

_DATA_LAG_WARNING = "Note: Call Records API may have up to 15 minutes latency for recent calls."


async def _get_user_call_records(upn: str, days: int) -> list[dict[str, Any]]:
    since = days_ago(days)
    params = {
        "$filter": f"participants/any(p:p/identity/user/userPrincipalName eq '{upn}') and startDateTime ge '{since}'",
        "$top": "50",
        "$orderby": "startDateTime desc",
    }
    data = await graph_get(
        "/communications/callRecords",
        scopes=SCOPES["call_records"],
        params=params,
    )
    return data.get("value", [])


async def get_call_quality_summary(upn: str, days: int = 7) -> dict[str, Any]:
    records = await _get_user_call_records(upn, days)
    total = len(records)
    failed = [r for r in records if r.get("result", "").lower() not in ("success", "")]
    lines = [f"## Call Quality Summary: {upn} (last {days} days)", _DATA_LAG_WARNING]
    lines.append(f"- **Total calls:** {total}")
    lines.append(f"- **Failed calls:** {len(failed)}")
    if total > 0:
        lines.append(f"- **Success rate:** {(total - len(failed)) / total * 100:.1f}%")
    return {
        "upn": upn,
        "days": days,
        "total_calls": total,
        "failed_calls": len(failed),
        "records": records,
        "data_lag_warning": _DATA_LAG_WARNING,
        "markdown": "\n".join(lines),
    }


async def diagnose_call_quality(call_id: str) -> dict[str, Any]:
    record = await graph_get(
        endpoints.call_record(call_id),
        scopes=SCOPES["call_records"],
        cache_key=f"callrecord:{call_id}",
        ttl=settings.cache_ttl_calls,
    )
    sessions_data = await graph_get(
        endpoints.call_record_sessions(call_id),
        scopes=SCOPES["call_records"],
        cache_key=f"callsessions:{call_id}",
        ttl=settings.cache_ttl_calls,
    )
    sessions = sessions_data.get("value", [])
    result = record.get("result", "unknown")
    participants = record.get("participants", [])
    lines = [
        f"## Call Diagnosis: {call_id}",
        _DATA_LAG_WARNING,
        f"- **Result:** {result}",
        f"- **Participants:** {len(participants)}",
        f"- **Sessions:** {len(sessions)}",
        f"- **Start:** {record.get('startDateTime', 'N/A')}",
    ]
    if result.lower() != "success":
        failure_info = record.get("failureInfo", {})
        lines.append(f"- **Failure reason:** {failure_info.get('reason', 'unknown')}")
    return {
        "call_id": call_id,
        "result": result,
        "participant_count": len(participants),
        "session_count": len(sessions),
        "record": record,
        "sessions": sessions,
        "data_lag_warning": _DATA_LAG_WARNING,
        "markdown": "\n".join(lines),
    }


async def list_failed_calls(upn: str, days: int = 7) -> dict[str, Any]:
    records = await _get_user_call_records(upn, days)
    failed = [r for r in records if r.get("result", "").lower() not in ("success", "")]
    lines = [f"## Failed Calls: {upn} (last {days} days)", _DATA_LAG_WARNING, f"- **Count:** {len(failed)}"]
    for r in failed:
        lines.append(f"\n- **{r.get('startDateTime', '?')}** — result: {r.get('result', '?')} | id: {r.get('id', '?')}")
    return {
        "upn": upn,
        "days": days,
        "failed_calls": failed,
        "count": len(failed),
        "data_lag_warning": _DATA_LAG_WARNING,
        "markdown": "\n".join(lines),
    }


async def list_poor_quality_calls(upn: str, days: int = 7) -> dict[str, Any]:
    records = await _get_user_call_records(upn, days)
    # Flag successful calls that might have quality issues (heuristic: no modalities data)
    poor = [r for r in records if r.get("result", "").lower() == "success" and not r.get("modalities")]
    lines = [f"## Poor Quality Calls: {upn} (last {days} days)", _DATA_LAG_WARNING, f"- **Count:** {len(poor)}"]
    lines.append("\n*Note: Full quality metrics require session-level data via diagnose_call_quality.*")
    return {
        "upn": upn,
        "days": days,
        "poor_quality_calls": poor,
        "count": len(poor),
        "data_lag_warning": _DATA_LAG_WARNING,
        "markdown": "\n".join(lines),
    }
